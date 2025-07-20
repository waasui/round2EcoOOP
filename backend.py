from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
import uvicorn
from datetime import datetime
from db import EcoTracker, EcoAction, Challenge


class ActionRequest(BaseModel):
    action: str
    points: int

class ActionResponse(BaseModel):
    status: str
    message: str
    action_logged: Optional[str] = None
    points_earned: Optional[int] = None

class StatsResponse(BaseModel):
    total_points: int
    weekly_points: int
    total_actions: int
    current_streak: int
    longest_streak: int


class EcoBackendService:
    
    def __init__(self):
        self.tracker = EcoTracker()
    

    def log_eco_action(self, action: str, points: int) -> Dict[str, Any]:
        try:
            if not action or not action.strip():
                raise ValueError("Action cannot be empty")
            
            if points <= 0:
                raise ValueError("Points must be positive")
            
            success = self.tracker.log_action(action.strip(), points)
            
            if success:
                return {
                    "status": "success",
                    "message": f"Successfully logged {action}",
                    "action_logged": action.strip(),
                    "points_earned": points
                }
            else:
                raise Exception("Failed to log action in database")
                
        except ValueError as ve:
            return {
                "status": "error",
                "message": str(ve)
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Internal error: {str(e)}"
            }
    

    def get_user_stats(self) -> Dict[str, Any]:
        try:
            stats = self.tracker.get_stats()
            current_streak, longest_streak = stats['streak_data']
            
            return {
                "status": "success",
                "data": {
                    "total_points": stats['total_points'],
                    "weekly_points": stats['weekly_points'],
                    "total_actions": stats['total_actions'],
                    "current_streak": current_streak,
                    "longest_streak": longest_streak,
                    "recent_actions": stats['action_history'][:5],  # Last 5 actions
                    "active_challenges": len([c for c in stats['challenges'] if not c[4]]),  # Not completed
                    "completed_challenges": len([c for c in stats['challenges'] if c[4]])  # Completed
                }
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to get stats: {str(e)}"
            }
    

    def get_challenges(self) -> Dict[str, Any]:
        try:
            challenges = self.tracker.challenge_manager.get_challenges()
            formatted_challenges = []
            
            for name, desc, current, target, completed in challenges:
                formatted_challenges.append({
                    "name": name,
                    "description": desc,
                    "current_count": current,
                    "target_count": target,
                    "completed": bool(completed),
                    "progress_percentage": min(100, (current / target) * 100) if target > 0 else 0
                })
            
            return {
                "status": "success",
                "data": formatted_challenges
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to get challenges: {str(e)}"
            }
    

    def reset_user_data(self) -> Dict[str, Any]:
        try:
            success = self.tracker.reset_all_data()
            if success:
                return {
                    "status": "success",
                    "message": "All data has been reset successfully"
                }
            else:
                return {
                    "status": "error",
                    "message": "Failed to reset data"
                }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Reset failed: {str(e)}"
            }


class EcoBackendApp:
    
    def __init__(self):
        self.app = FastAPI(
            title="Eco Tracker API",
            description="Backend API for the Round-2-Eco application",
            version="2.0.0"
        )
        self.service = EcoBackendService()
        self._setup_routes()
    

    def _setup_routes(self):
        
        @self.app.get("/")
        async def root():
            return {
                "message": "Eco backend working!",
                "version": "2.0.0",
                "timestamp": datetime.now().isoformat()
            }
        

        @self.app.post("/log", response_model=ActionResponse)
        async def log_action(action_data: ActionRequest):
            result = self.service.log_eco_action(action_data.action, action_data.points)
            
            if result["status"] == "error":
                raise HTTPException(status_code=400, detail=result["message"])
            
            return ActionResponse(**result)
        

        @self.app.get("/stats")
        async def get_stats():
            result = self.service.get_user_stats()
            
            if result["status"] == "error":
                raise HTTPException(status_code=500, detail=result["message"])
            
            return result
        

        @self.app.get("/challenges")
        async def get_challenges():
            result = self.service.get_challenges()
            
            if result["status"] == "error":
                raise HTTPException(status_code=500, detail=result["message"])
            
            return result
        

        @self.app.post("/reset")
        async def reset_data():
            result = self.service.reset_user_data()
            
            if result["status"] == "error":
                raise HTTPException(status_code=500, detail=result["message"])
            
            return result
        

        @self.app.get("/health")
        async def health_check():
            try:
                total_points = self.service.tracker.points_manager.get_total_points()
                return {
                    "status": "healthy",
                    "database": "connected",
                    "timestamp": datetime.now().isoformat(),
                    "sample_data": f"Total points in system: {total_points}"
                }
            except Exception as e:
                raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")
        

        @self.app.get("/history")
        async def get_action_history():
            try:
                history = self.service.tracker.action_manager.get_action_history()
                formatted_history = [
                    {
                        "action": action,
                        "points": points,
                        "timestamp": timestamp
                    }
                    for action, points, timestamp in history[:20]
                ]
                return {
                    "status": "success",
                    "data": formatted_history,
                    "total_count": len(history)
                }
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to get history: {str(e)}")


app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Eco backend working!"}

@app.post("/log")
def log_action(action: str):
    return {"status": "success", "logged_action": action}

eco_app = EcoBackendApp()
new_app = eco_app.app


if __name__ == "__main__":
    print("🚀 Starting Eco Tracker Backend (Object-Oriented Version)")
    print("📡 API Documentation available at: http://localhost:8000/docs")
    print("🔍 Health Check: http://localhost:8000/health")

    uvicorn.run(new_app, host="0.0.0.0", port=8000, reload=True)