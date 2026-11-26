from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
import function as f

app = FastAPI()
class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str
  
class LoginRequest(BaseModel):
    email: str
    password: str

class RefreshRequest(BaseModel):
    refresh_token: str

class ManagerRequest(BaseModel):
    username: str
    email: str
    password: str

class MissionRequest(BaseModel):
    title: str
    description: str
    difficulty: str
    location: str
    reward: str

class UpdateMissionRequest(BaseModel):
    title: str
    description: str
    difficulty: str
    location: str
    reward: str
    is_active: bool

class SubmitRequest(BaseModel):
    mission_id: int
    details: str

class ReviewRequest(BaseModel):
    mission_id: int
    player_id: int
    approved: bool

class RewardRequest(BaseModel):
    mission_id: int
    name: str
    description: str

class AssignRewardRequest(BaseModel):
    reward_id: int
    player_id: int

def get_user(token):
    data = f.verify_token(token)
    if data is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    if data["type"] != "access":
        raise HTTPException(status_code=401, detail="Access token required")
    return data

def check_role(user, role):
    if user["role"] != role:
        raise HTTPException(status_code=403, detail="You don't have permission")

@app.post("/auth/register")
def register(request: RegisterRequest):
    user_id = f.register_user(request.username, request.email, request.password)
    if user_id is None:
        raise HTTPException(status_code=400, detail="Email already exists")
    return {"message": "Registration successful", "user_id": user_id}

@app.post("/auth/login")
def login(request: LoginRequest):
    result = f.login_user(request.email, request.password)
    if result is None:
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    return result

@app.post("/auth/refresh")
def refresh(request: RefreshRequest):
    new_token = f.refresh_token_function(request.refresh_token)
    if new_token is None:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    return {"access_token": new_token, "token_type": "bearer"}


@app.post("/admin/managers")
def add_manager(request: ManagerRequest, token: str = Header(None)):
    user = get_user(token)
    check_role(user, "admin")
    manager_id = f.create_manager(request.username, request.email, request.password)
    if manager_id is None:
        raise HTTPException(status_code=400, detail="Email already exists")
    return {"message": "Manager created", "manager_id": manager_id}


@app.post("/missions")
def add_mission(request: MissionRequest, token: str = Header(None)):
    user = get_user(token)
    check_role(user, "mission_manager")
    mission_id = f.create_mission(request.title, request.description, request.difficulty, request.location, request.reward, user["user_id"])
    return {"message": "Mission created", "mission_id": mission_id}

@app.get("/missions")
def list_missions(token: str = Header(None)):
    get_user(token)
    return f.get_all_missions()

@app.get("/missions/{mission_id}")
def mission_details(mission_id: int, token: str = Header(None)):
    get_user(token)
    mission = f.get_mission_by_id(mission_id)
    if mission is None:
        raise HTTPException(status_code=404, detail="Mission not found")
    return mission

@app.patch("/missions/{mission_id}")
def edit_mission(mission_id: int, request: UpdateMissionRequest, token: str = Header(None)):
    user = get_user(token)
    check_role(user, "mission_manager")
    result = f.update_mission(mission_id, request.title, request.description, request.difficulty, request.location, request.reward, request.is_active)
    if result is None:
        raise HTTPException(status_code=404, detail="Mission not found")
    return {"message": "Mission updated"}

@app.post("/missions/{mission_id}/accept")
def accept(mission_id: int, token: str = Header(None)):
    user = get_user(token)
    check_role(user, "player")
    record_id = f.accept_mission(user["user_id"], mission_id)
    if record_id is None:
        raise HTTPException(status_code=400, detail="Mission unavailable or already accepted")
    return {"message": "Mission accepted", "record_id": record_id}

@app.get("/players/me/missions")
def my_missions(token: str = Header(None)):
    user = get_user(token)
    check_role(user, "player")
    return f.get_accepted_missions(user["user_id"])

@app.post("/players/me/submit")
def submit(request: SubmitRequest, token: str = Header(None)):
    user = get_user(token)
    check_role(user, "player")
    result = f.submit_mission(user["user_id"], request.mission_id, request.details)
    if result is None:
        raise HTTPException(status_code=400, detail="Mission not accepted or already submitted")
    return {"message": "Mission submitted for review"}

@app.post("/missions/review")
def review(request: ReviewRequest, token: str = Header(None)):
    user = get_user(token)
    check_role(user, "mission_manager")
    result = f.review_mission(request.mission_id, request.player_id, request.approved)
    if result is None:
        raise HTTPException(status_code=404, detail="Submission not found")
    return {"message": "Submission reviewed"}

@app.get("/players/me/history")
def my_history(token: str = Header(None)):
    user = get_user(token)
    check_role(user, "player")
    return f.get_completed_history(user["user_id"])

@app.post("/rewards")
def add_reward(request: RewardRequest, token: str = Header(None)):
    user = get_user(token)
    check_role(user, "mission_manager")
    reward_id = f.create_reward(request.mission_id, request.name, request.description)
    if reward_id is None:
        raise HTTPException(status_code=404, detail="Mission not found")
    return {"message": "Reward created", "reward_id": reward_id}

@app.get("/rewards")
def list_rewards(token: str = Header(None)):
    get_user(token)
    return f.get_available_rewards()

@app.post("/rewards/assign")
def give_reward(request: AssignRewardRequest, token: str = Header(None)):
    user = get_user(token)
    check_role(user, "mission_manager")
    result = f.assign_reward(request.reward_id, request.player_id)
    if result is None:
        raise HTTPException(status_code=400, detail="Reward unavailable or mission not completed")
    return {"message": "Reward assigned"}

@app.get("/leaderboard")
def leaderboard(token: str = Header(None)):
    get_user(token)
    return f.get_leaderboard()

@app.get("/players/me/profile")
def profile(token: str = Header(None)):
    user = get_user(token)
    result = f.get_profile(user["user_id"])
    if result is None:
        raise HTTPException(status_code=404, detail="User not found")
    return result

