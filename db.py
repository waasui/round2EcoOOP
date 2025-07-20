import sqlite3
from datetime import datetime, timedelta
from typing import List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class EcoAction:
    action: str
    points: int
    timestamp: str
    id: Optional[int] = None


@dataclass
class Challenge:
    name: str
    description: str
    target_count: int
    current_count: int = 0
    completed: bool = False
    created_date: str = ""
    completed_date: Optional[str] = None
    id: Optional[int] = None


@dataclass
class StreakData:
    current_streak: int = 0
    longest_streak: int = 0
    last_action_date: Optional[str] = None
    id: Optional[int] = None


class EcoDatabase:
    
    def __init__(self, db_name: str = "eco_tracker.db"):
        self.db_name = db_name
        self.init_db()
    

    def _get_connection(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_name)
    

    def init_db(self) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("PRAGMA table_info(actions)")
            columns = cursor.fetchall()
            
            if not columns or not any(col[1] == 'points' for col in columns):
                print("Recreating actions table with correct schema...")
                cursor.execute("DROP TABLE IF EXISTS actions")
                cursor.execute('''
                    CREATE TABLE actions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        action TEXT NOT NULL,
                        points INTEGER NOT NULL,
                        timestamp TEXT NOT NULL
                    )
                ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS challenges (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL,
                    target_count INTEGER NOT NULL,
                    current_count INTEGER DEFAULT 0,
                    completed BOOLEAN DEFAULT 0,
                    created_date TEXT NOT NULL,
                    completed_date TEXT
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS streak_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    current_streak INTEGER DEFAULT 0,
                    longest_streak INTEGER DEFAULT 0,
                    last_action_date TEXT
                )
            ''')
            
            self._initialize_default_data(cursor)
            
            conn.commit()
    
    def _initialize_default_data(self, cursor: sqlite3.Cursor) -> None:
        cursor.execute("SELECT COUNT(*) FROM streak_data")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO streak_data (current_streak, longest_streak) VALUES (0, 0)")
        
        cursor.execute("SELECT COUNT(*) FROM challenges")
        if cursor.fetchone()[0] == 0:
            default_challenges = [
                ("Eco Beginner", "Complete 10 eco-actions", 10),
                ("Green Warrior", "Complete 20 eco-actions in a month", 20),
                ("Eco Champion", "Complete 50 eco-actions", 50),
                ("Planet Protector", "Complete 100 eco-actions", 100),
                ("Recycling Master", "Recycle 15 times", 15),
                ("Transport Hero", "Use eco-transport 25 times", 25)
            ]
            
            for name, desc, target in default_challenges:
                cursor.execute(
                    "INSERT INTO challenges (name, description, target_count, created_date) VALUES (?, ?, ?, ?)",
                    (name, desc, target, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                )


class ActionManager:
    
    def __init__(self, db: EcoDatabase):
        self.db = db
    

    def add_action(self, action: str, points: int) -> bool:
        try:
            with self.db._get_connection() as conn:
                cursor = conn.cursor()
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                cursor.execute("INSERT INTO actions (action, points, timestamp) VALUES (?, ?, ?)",
                             (action, points, timestamp))
                
                streak_manager = StreakManager(self.db)
                challenge_manager = ChallengeManager(self.db)
                
                streak_manager.update_streak(cursor)
                challenge_manager.update_challenges(cursor, action)
                
                conn.commit()
                return True
        except Exception as e:
            print(f"❌ Error adding action: {e}")
            return False
    

    def get_action_history(self) -> List[Tuple[str, int, str]]:
        try:
            with self.db._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT action, points, timestamp FROM actions ORDER BY timestamp DESC")
                return cursor.fetchall()
        except sqlite3.OperationalError:
            return []
    
    def get_total_action_count(self, cursor: Optional[sqlite3.Cursor] = None) -> int:
        if cursor:
            cursor.execute("SELECT COUNT(*) FROM actions")
            return cursor.fetchone()[0]
        
        try:
            with self.db._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM actions")
                return cursor.fetchone()[0]
        except sqlite3.OperationalError:
            return 0


class PointsManager:
    
    def __init__(self, db: EcoDatabase):
        self.db = db
    

    def get_total_points(self) -> int:
        try:
            with self.db._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT SUM(points) FROM actions")
                result = cursor.fetchone()[0]
                return result if result else 0
        except sqlite3.OperationalError:
            return 0
    

    def get_weekly_points(self) -> int:
        try:
            with self.db._get_connection() as conn:
                cursor = conn.cursor()
                one_week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
                cursor.execute("SELECT SUM(points) FROM actions WHERE timestamp >= ?", (one_week_ago,))
                result = cursor.fetchone()[0]
                return result if result else 0
        except sqlite3.OperationalError:
            return 0
    

    def get_points_per_day_last_week(self) -> List[Tuple[str, int]]:
        try:
            with self.db._get_connection() as conn:
                cursor = conn.cursor()
                
                today = datetime.now().date()
                seven_days_ago = today - timedelta(days=6)
                
                cursor.execute("""
                    SELECT DATE(timestamp) as day, SUM(points)
                    FROM actions
                    WHERE DATE(timestamp) BETWEEN ? AND ?
                    GROUP BY day
                    ORDER BY day ASC
                """, (seven_days_ago.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")))
                
                rows = cursor.fetchall()
                
                daily_points = {(seven_days_ago + timedelta(days=i)).strftime("%Y-%m-%d"): 0 
                              for i in range(7)}
                
                for day, points in rows:
                    daily_points[day] = points if points else 0
                
                return list(daily_points.items())
        except sqlite3.OperationalError:
            return []


class StreakManager:
    
    def __init__(self, db: EcoDatabase):
        self.db = db
    
    def update_streak(self, cursor: sqlite3.Cursor) -> None:
        today = datetime.now().date()
        
        cursor.execute("SELECT current_streak, longest_streak, last_action_date FROM streak_data ORDER BY id DESC LIMIT 1")
        result = cursor.fetchone()
        
        if result:
            current_streak, longest_streak, last_action_date = result
            
            if last_action_date:
                last_date = datetime.strptime(last_action_date.split()[0], "%Y-%m-%d").date()
                
                if last_date == today:
                    return
                elif last_date == today - timedelta(days=1):
                    current_streak += 1
                else:
                    current_streak = 1
            else:
                current_streak = 1
            
            longest_streak = max(longest_streak, current_streak)
            
            cursor.execute(
                "UPDATE streak_data SET current_streak = ?, longest_streak = ?, last_action_date = ? WHERE id = (SELECT MAX(id) FROM streak_data)",
                (current_streak, longest_streak, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            )
    

    def get_streak_data(self) -> Tuple[int, int]:
        try:
            with self.db._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT current_streak, longest_streak FROM streak_data ORDER BY id DESC LIMIT 1")
                result = cursor.fetchone()
                return result if result else (0, 0)
        except sqlite3.OperationalError:
            return (0, 0)


class ChallengeManager:
    
    def __init__(self, db: EcoDatabase):
        self.db = db
    

    def update_challenges(self, cursor: sqlite3.Cursor, action: str) -> None:
        action_manager = ActionManager(self.db)
        total_actions = action_manager.get_total_action_count(cursor)
        
        cursor.execute(
            "UPDATE challenges SET current_count = ? WHERE name IN ('Eco Beginner', 'Green Warrior', 'Eco Champion', 'Planet Protector')",
            (total_actions,)
        )
        
        if action == "Recycle":
            cursor.execute("SELECT COUNT(*) FROM actions WHERE action = 'Recycle'")
            recycle_count = cursor.fetchone()[0]
            cursor.execute("UPDATE challenges SET current_count = ? WHERE name = 'Recycling Master'", (recycle_count,))
        
        if action in ["Bike", "Walk", "Public Transport"]:
            cursor.execute("SELECT COUNT(*) FROM actions WHERE action IN ('Bike', 'Walk', 'Public Transport')")
            transport_count = cursor.fetchone()[0]
            cursor.execute("UPDATE challenges SET current_count = ? WHERE name = 'Transport Hero'", (transport_count,))
        
        cursor.execute(
            "UPDATE challenges SET completed = 1, completed_date = ? WHERE current_count >= target_count AND completed = 0",
            (datetime.now().strftime("%Y-%m-%d %H:%M:%S"),)
        )
    

    def get_challenges(self) -> List[Tuple]:
        try:
            with self.db._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT name, description, current_count, target_count, completed FROM challenges ORDER BY completed ASC, id ASC")
                return cursor.fetchall()
        except sqlite3.OperationalError:
            return []


class EcoTracker:
    
    def __init__(self, db_name: str = "eco_tracker.db"):
        self.db = EcoDatabase(db_name)
        self.action_manager = ActionManager(self.db)
        self.points_manager = PointsManager(self.db)
        self.streak_manager = StreakManager(self.db)
        self.challenge_manager = ChallengeManager(self.db)
    

    def log_action(self, action: str, points: int) -> bool:
        return self.action_manager.add_action(action, points)
    

    def get_stats(self) -> dict:
        return {
            'total_points': self.points_manager.get_total_points(),
            'weekly_points': self.points_manager.get_weekly_points(),
            'total_actions': self.action_manager.get_total_action_count(),
            'streak_data': self.streak_manager.get_streak_data(),
            'challenges': self.challenge_manager.get_challenges(),
            'action_history': self.action_manager.get_action_history(),
            'daily_points_last_week': self.points_manager.get_points_per_day_last_week()
        }
    

    def reset_all_data(self) -> bool:
        try:
            with self.db._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("SELECT COUNT(*) FROM actions")
                print("🧪 Before reset:", cursor.fetchone()[0])
                
                cursor.execute("DELETE FROM actions")
                cursor.execute("DELETE FROM sqlite_sequence WHERE name='actions'")
                cursor.execute("UPDATE challenges SET current_count = 0, completed = 0, completed_date = NULL")
                cursor.execute("UPDATE streak_data SET current_streak = 0, last_action_date = NULL")
                
                cursor.execute("SELECT COUNT(*) FROM actions")
                print("🧪 After reset:", cursor.fetchone()[0])
                
                conn.commit()
                return True
        except Exception as ex:
            print(f"❌ Database error: {ex}")
            return False


def init_db():
    tracker = EcoTracker()
    return tracker

def insert_action(action, points):
    tracker = EcoTracker()
    tracker.log_action(action, points)

def get_total_points():
    tracker = EcoTracker()
    return tracker.points_manager.get_total_points()

def get_weekly_points():
    tracker = EcoTracker()
    return tracker.points_manager.get_weekly_points()

def get_challenges():
    tracker = EcoTracker()
    return tracker.challenge_manager.get_challenges()

def get_streak_data():
    tracker = EcoTracker()
    return tracker.streak_manager.get_streak_data()

def get_action_history():
    tracker = EcoTracker()
    return tracker.action_manager.get_action_history()

def reset_all_data():
    tracker = EcoTracker()
    return tracker.reset_all_data()

def get_points_per_day_last_week():
    tracker = EcoTracker()
    return tracker.points_manager.get_points_per_day_last_week()


if __name__ == "__main__":
    tracker = EcoTracker()
    
    tracker.log_action("Recycle", 10)
    tracker.log_action("Bike", 15)
    
    stats = tracker.get_stats()
    print("📊 Your Eco Stats:")
    print(f"Total Points: {stats['total_points']}")
    print(f"Current Streak: {stats['streak_data'][0]} days")
    print(f"Total Actions: {stats['total_actions']}")