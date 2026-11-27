from sqlalchemy import create_engine, Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime, timedelta
import jwt
from argon2 import PasswordHasher

engine = create_engine("sqlite:///gta.db")
Base = declarative_base()
Session = sessionmaker(bind=engine)
SECRET_KEY = "CHANGE_THIS_TO_A_VERY_LONG_PRIVATE_SECRET_KEY_1234"
ALGORITHM = "HS256"
password_hasher = PasswordHasher()

class Users(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String)
    email = Column(String, unique=True)
    hashed_password = Column(String)
    role = Column(String, default="player")
    xp = Column(Integer, default=0)

class Missions(Base):
    __tablename__ = "missions"
    id = Column(Integer, primary_key=True)
    title = Column(String)
    description = Column(String)
    difficulty = Column(String)
    location = Column(String)
    reward = Column(String)
    is_active = Column(Boolean, default=True)
    created_by = Column(Integer, ForeignKey("users.id"))

class PlayerMissions(Base):
    __tablename__ = "player_missions"
    id = Column(Integer, primary_key=True)
    player_id = Column(Integer, ForeignKey("users.id"))
    mission_id = Column(Integer, ForeignKey("missions.id"))
    status = Column(String, default="accepted")
    submission_details = Column(String)
    accepted_at = Column(String)
    completed_at = Column(String)

class Rewards(Base):
    __tablename__ = "rewards"
    id = Column(Integer, primary_key=True)
    mission_id = Column(Integer, ForeignKey("missions.id"))
    name = Column(String)
    description = Column(String)
    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=True)

Base.metadata.create_all(engine)

def create_token(user_id, role, token_type):
    if token_type == "access":
        expiry = datetime.utcnow() + timedelta(minutes=15)
    else:
        expiry = datetime.utcnow() + timedelta(days=7)
    token_data = {
        "user_id": user_id,
        "role": role,
        "type": token_type,
        "exp": expiry
    }
    token = jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)
    return token

def verify_token(token):
    try:
        data = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return data
    except:
        return None

def register_user(username, email, password):
    session = Session()
    existing_user = session.query(Users).filter(Users.email == email).first()
    if existing_user:
        session.close()
        return None
    hashed_password = password_hasher.hash(password)
    user = Users(username=username, email=email, hashed_password=hashed_password, role="player")
    session.add(user)
    session.commit()
    user_id = user.id
    session.close()
    return user_id

def login_user(email, password):
    session = Session()
    user = session.query(Users).filter(Users.email == email).first()
    if user is None:
        session.close()
        return None
    try:
        password_hasher.verify(user.hashed_password, password)
    except:
        session.close()
        return None
    access_token = create_token(user.id, user.role, "access")
    refresh_token = create_token(user.id, user.role, "refresh")
    result = {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }
    session.close()
    return result

def refresh_token_function(refresh_token):
    data = verify_token(refresh_token)
    if data is None:
        return None
    if data["type"] != "refresh":
        return None
    new_access_token = create_token(data["user_id"], data["role"], "access")
    return new_access_token

def create_manager(username, email, password):
    session = Session()
    existing_user = session.query(Users).filter(Users.email == email).first()
    if existing_user:
        session.close()
        return None
    hashed_password = password_hasher.hash(password)
    manager = Users(username=username, email=email, hashed_password=hashed_password, role="mission_manager")
    session.add(manager)
    session.commit()
    manager_id = manager.id
    session.close()
    return manager_id

def create_mission(title, description, difficulty, location, reward, manager_id):
    session = Session()
    mission = Missions(title=title, description=description, difficulty=difficulty, location=location, reward=reward, is_active=True, created_by=manager_id)
    session.add(mission)
    session.commit()
    mission_id = mission.id
    session.close()
    return mission_id

def get_all_missions():
    session = Session()
    missions = session.query(Missions).filter(Missions.is_active == True).all()
    result = []
    for mission in missions:
        result.append({
            "id": mission.id,
            "title": mission.title,
            "description": mission.description,
            "difficulty": mission.difficulty,
            "location": mission.location,
            "reward": mission.reward
        })
    session.close()
    return result

def get_mission_by_id(mission_id):
    session = Session()
    mission = session.get(Missions, mission_id)
    if mission is None:
        session.close()
        return None
    result = {
        "id": mission.id,
        "title": mission.title,
        "description": mission.description,
        "difficulty": mission.difficulty,
        "location": mission.location,
        "reward": mission.reward,
        "is_active": mission.is_active
    }
    session.close()
    return result

def update_mission(mission_id, title, description, difficulty, location, reward, is_active):
    session = Session()
    mission = session.get(Missions, mission_id)
    if mission is None:
        session.close()
        return None
    mission.title = title
    mission.description = description
    mission.difficulty = difficulty
    mission.location = location
    mission.reward = reward
    mission.is_active = is_active
    session.commit()
    session.close()
    return True

def accept_mission(player_id, mission_id):
    session = Session()
    mission = session.get(Missions, mission_id)
    if mission is None or mission.is_active == False:
        session.close()
        return None
    existing = session.query(PlayerMissions).filter(
        PlayerMissions.player_id == player_id,
        PlayerMissions.mission_id == mission_id,
        PlayerMissions.status != "rejected"
    ).first()
    if existing:
        session.close()
        return None
    player_mission = PlayerMissions(
        player_id=player_id,
        mission_id=mission_id,
        status="accepted",
        accepted_at=str(datetime.utcnow())
    )
    session.add(player_mission)
    session.commit()
    record_id = player_mission.id
    session.close()
    return record_id

def get_accepted_missions(player_id):
    session = Session()
    records = session.query(PlayerMissions).filter(
        PlayerMissions.player_id == player_id,
        PlayerMissions.status == "accepted"
    ).all()
    result = []
    for record in records:
        mission = session.get(Missions, record.mission_id)
        if mission:
            result.append({
                "mission_id": mission.id,
                "title": mission.title,
                "status": record.status
            })
    session.close()
    return result

def submit_mission(player_id, mission_id, details):
    session = Session()
    record = session.query(PlayerMissions).filter(
        PlayerMissions.player_id == player_id,
        PlayerMissions.mission_id == mission_id,
        PlayerMissions.status == "accepted"
    ).first()
    if record is None:
        session.close()
        return None
    record.status = "submitted"
    record.submission_details = details
    session.commit()
    session.close()
    return True

def review_mission(mission_id, player_id, approved):
    session = Session()
    record = session.query(PlayerMissions).filter(
        PlayerMissions.mission_id == mission_id,
        PlayerMissions.player_id == player_id,
        PlayerMissions.status == "submitted"
    ).first()
    if record is None:
        session.close()
        return None
    if approved:
        record.status = "completed"
        record.completed_at = str(datetime.utcnow())
        mission = session.get(Missions, mission_id)
        player = session.get(Users, player_id)
        if mission and player:
            if mission.difficulty == "easy":
                player.xp += 50
            elif mission.difficulty == "medium":
                player.xp += 100
            elif mission.difficulty == "hard":
                player.xp += 200
            elif mission.difficulty == "special":
                player.xp += 500
    else:
        record.status = "rejected"
    session.commit()
    session.close()
    return True

def get_completed_history(player_id):
    session = Session()
    records = session.query(PlayerMissions).filter(
        PlayerMissions.player_id == player_id,
        PlayerMissions.status == "completed"
    ).all()
    result = []
    for record in records:
        mission = session.get(Missions, record.mission_id)
        if mission:
            result.append({
                "mission_id": mission.id,
                "title": mission.title,
                "completed_at": record.completed_at
            })
    session.close()
    return result

def create_reward(mission_id, name, description):
    session = Session()
    mission = session.get(Missions, mission_id)
    if mission is None:
        session.close()
        return None
    reward = Rewards(mission_id=mission_id, name=name, description=description)
    session.add(reward)
    session.commit()
    reward_id = reward.id
    session.close()
    return reward_id

def get_available_rewards():
    session = Session()
    rewards = session.query(Rewards).filter(Rewards.assigned_to == None).all()
    result = []
    for reward in rewards:
        result.append({
            "id": reward.id,
            "mission_id": reward.mission_id,
            "name": reward.name,
            "description": reward.description
        })
    session.close()
    return result

def assign_reward(reward_id, player_id):
    session = Session()
    reward = session.get(Rewards, reward_id)
    if reward is None or reward.assigned_to is not None:
        session.close()
        return None
    completed = session.query(PlayerMissions).filter(
        PlayerMissions.player_id == player_id,
        PlayerMissions.mission_id == reward.mission_id,
        PlayerMissions.status == "completed"
    ).first()
    if completed is None:
        session.close()
        return None
    reward.assigned_to = player_id
    session.commit()
    session.close()
    return True

def get_leaderboard():
    session = Session()
    players = session.query(Users).filter(Users.role == "player").order_by(Users.xp.desc()).all()
    result = []
    for player in players:
        result.append({
            "username": player.username,
            "xp": player.xp
        })
    session.close()
    return result

def get_profile(player_id):
    session = Session()
    player = session.get(Users, player_id)
    if player is None:
        session.close()
        return None
    completed_count = session.query(PlayerMissions).filter(
        PlayerMissions.player_id == player_id,
        PlayerMissions.status == "completed"
    ).count()
    result = {
        "id": player.id,
        "username": player.username,
        "email": player.email,
        "xp": player.xp,
        "completed_missions": completed_count
    }
    session.close()
    return result

