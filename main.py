import flet as ft
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import io
import base64
from typing import Dict, Set, Any, Optional, List
from dataclasses import dataclass
from db import EcoTracker


@dataclass
class AppConfig:
    POINTS: Dict[str, int] = None
    WEEKLY_CAP: int = 1000
    ACHIEVEMENT_MILESTONES: List[int] = None
    THEME_COLORS: Dict[str, str] = None
    
    def __post_init__(self):
        if self.POINTS is None:
            self.POINTS = {
                "Recycle": 10,
                "Bike": 20,
                "Walk": 15,
                "Public Transport": 15,
                "Plant Seed": 30,
                "Pick Up Trash": 5
            }
        
        if self.ACHIEVEMENT_MILESTONES is None:
            self.ACHIEVEMENT_MILESTONES = [50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 1000]
        
        if self.THEME_COLORS is None:
            self.THEME_COLORS = {
                "primary": "#4CAF50",
                "secondary": "#2E7D32",
                "background": "#F1F8E9",
                "surface": "#FFFFFF",
                "accent": "#FF9800"
            }


class ChartGenerator:
    
    def __init__(self, config: AppConfig):
        self.config = config
    
    def generate_weekly_chart(self, data: List[tuple]) -> str:
        if not data:
            return ""

        days, points = zip(*data)
        
        plt.style.use('seaborn-v0_8')
        fig, ax = plt.subplots(figsize=(8, 5))
        bars = ax.bar(days, points, color=self.config.THEME_COLORS["primary"], 
                     alpha=0.8, edgecolor=self.config.THEME_COLORS["secondary"], linewidth=1.2)
        
        for bar in bars:
            height = bar.get_height()
            if height > 0:
                ax.text(bar.get_x() + bar.get_width()/2., height + 1,
                       f'{int(height)}', ha='center', va='bottom', fontsize=9, fontweight='bold')
        
        ax.set_title("🌱 Eco Points - Last 7 Days", fontsize=14, fontweight='bold', 
                    color=self.config.THEME_COLORS["secondary"])
        ax.set_ylabel("Points", fontweight='bold')
        ax.set_xlabel("Date", fontweight='bold')
        ax.grid(True, alpha=0.3)
        plt.xticks(rotation=45, fontsize=8)
        plt.tight_layout()

        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=150, bbox_inches='tight')
        buf.seek(0)
        encoded = base64.b64encode(buf.read()).decode("utf-8")
        plt.close()
        return f"data:image/png;base64,{encoded}"


class AchievementSystem:
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.earned_achievements: Set[int] = set()
    

    def get_achievement_emoji(self, milestone: int) -> str:
        if milestone < 400:
            return "🥉"
        elif milestone < 800:
            return "🥈"
        else:
            return "🥇"
    

    def check_new_achievements(self, old_points: int, new_points: int) -> List[int]:
        new_achievements = []
        
        for milestone in self.config.ACHIEVEMENT_MILESTONES:
            if old_points < milestone <= new_points and milestone not in self.earned_achievements:
                self.earned_achievements.add(milestone)
                new_achievements.append(milestone)
        
        return new_achievements
    

    def load_existing_achievements(self, total_points: int) -> None:
        for milestone in self.config.ACHIEVEMENT_MILESTONES:
            if total_points >= milestone:
                self.earned_achievements.add(milestone)
    

    def create_achievement_widget(self, milestone: int) -> ft.Container:
        emoji = self.get_achievement_emoji(milestone)
        return ft.Container(
            content=ft.Text(f"{emoji} {milestone} Points Achievement!", size=14, 
                          color=ft.Colors.WHITE, weight="bold"),
            bgcolor=ft.Colors.ORANGE,
            padding=10,
            border_radius=5,
            margin=ft.margin.only(bottom=5)
        )
    

    def reset_achievements(self) -> None:
        self.earned_achievements.clear()


class UIComponentFactory:
    
    def __init__(self, config: AppConfig):
        self.config = config
    

    def create_action_dropdown(self) -> ft.Dropdown:
        return ft.Dropdown(
            label="🌍 Choose Your Eco-Action",
            hint_text="Select an eco-friendly action...",
            options=[
                ft.dropdown.Option(key=name, text=f"{name} (+{points} pts)") 
                for name, points in self.config.POINTS.items()
            ],
            width=350,
            bgcolor=ft.Colors.WHITE,
            border_color=ft.Colors.GREEN,
            focused_border_color=ft.Colors.GREEN_800
        )
    

    def create_streak_card(self) -> ft.Card:
        return ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Icon("local_fire_department", color=ft.Colors.ORANGE, size=30),
                        ft.Text("Streak System", size=18, weight="bold", color=ft.Colors.ORANGE)
                    ], alignment=ft.MainAxisAlignment.CENTER),
                    ft.Text("Current: 0 days", size=14, text_align=ft.TextAlign.CENTER),
                    ft.Text("Best: 0 days", size=12, color=ft.Colors.GREY_700, text_align=ft.TextAlign.CENTER)
                ], spacing=5, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                padding=15
            ),
            elevation=3,
            color="#FFF3E0"
        )
    

    def create_history_table(self) -> ft.DataTable:
        return ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("🎯 Action", weight="bold")),
                ft.DataColumn(ft.Text("⭐ Points", weight="bold")),
                ft.DataColumn(ft.Text("📅 Date", weight="bold")),
            ],
            rows=[],
            bgcolor=ft.Colors.WHITE,
            border_radius=10,
            horizontal_lines=ft.border.BorderSide(1, ft.Colors.GREY_300)
        )
    

    def create_log_button(self, on_click_handler) -> ft.ElevatedButton:
        return ft.ElevatedButton(
            "🚀 Log Action",
            on_click=on_click_handler,
            bgcolor=ft.Colors.GREEN,
            color=ft.Colors.WHITE,
            height=50,
            width=200,
            style=ft.ButtonStyle(
                text_style=ft.TextStyle(size=16, weight="bold")
            )
        )
    

    def create_reset_button(self, on_click_handler) -> ft.OutlinedButton:
        return ft.OutlinedButton(
            "🔄 Reset All Data",
            on_click=on_click_handler,
            icon="restart_alt",
            height=40
        )


class UIDataManager:
    
    def __init__(self, tracker: EcoTracker, config: AppConfig):
        self.tracker = tracker
        self.config = config
    

    def get_action_emoji(self, action: str) -> str:
        emoji_map = {
            "Recycle": "♻️", 
            "Bike": "🚲", 
            "Walk": "🚶", 
            "Public Transport": "🚌", 
            "Plant Seed": "🌱", 
            "Pick Up Trash": "🗑️"
        }
        return emoji_map.get(action, "🌍")
    

    def create_history_row(self, action: str, points: int, timestamp: str) -> ft.DataRow:
        action_emoji = self.get_action_emoji(action)
        
        return ft.DataRow(cells=[
            ft.DataCell(ft.Text(f"{action_emoji} {action}")),
            ft.DataCell(ft.Text(f"+{points}", color=ft.Colors.GREEN, weight="bold")),
            ft.DataCell(ft.Text(timestamp.split()[0], size=12)),
        ])
    

    def create_challenge_card(self, name: str, description: str, current: int, 
                            target: int, completed: bool) -> ft.Card:
        progress = min(current / target, 1.0) if target > 0 else 0
        card_color = "#E8F5E8" if completed else "#FFFFFF"
        progress_color = ft.Colors.GREEN if completed else ft.Colors.BLUE
        
        return ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Icon("emoji_events" if completed else "flag", 
                               color=ft.Colors.GREEN if completed else ft.Colors.BLUE, size=20),
                        ft.Text(name, size=14, weight="bold", 
                               color=ft.Colors.GREEN if completed else ft.Colors.BLACK)
                    ]),
                    ft.Text(description, size=12, color=ft.Colors.GREY_700),
                    ft.ProgressBar(value=progress, color=progress_color, height=8),
                    ft.Text(f"{current}/{target} {'✅ Complete!' if completed else 'actions'}", 
                           size=11, color=ft.Colors.GREEN if completed else ft.Colors.GREY_600)
                ], spacing=5),
                padding=10
            ),
            elevation=2,
            color=card_color
        )


class EcoTrackerApp:
    
    def __init__(self):
        self.config = AppConfig()
        self.tracker = EcoTracker()
        self.chart_generator = ChartGenerator(self.config)
        self.achievement_system = AchievementSystem(self.config)
        self.ui_factory = UIComponentFactory(self.config)
        self.data_manager = UIDataManager(self.tracker, self.config)
        
        self.reset_stage = {"confirming": False}
        
        self._init_ui_components()
    

    def _init_ui_components(self):
        self.action_dropdown = self.ui_factory.create_action_dropdown()
        self.streak_card = self.ui_factory.create_streak_card()
        self.history_table = self.ui_factory.create_history_table()
        self.log_button = self.ui_factory.create_log_button(self._log_action)
        self.reset_button = self.ui_factory.create_reset_button(self._reset_points)
        
        self.total_points_text = ft.Text(
            f"Total Points: {self.tracker.points_manager.get_total_points()}", 
            size=20, weight="bold", color=ft.Colors.GREEN
        )
        
        self.achievements_column = ft.Column([])
        self.challenges_column = ft.Column([], spacing=10)
        
        chart_data = self.tracker.points_manager.get_points_per_day_last_week()
        chart_src = self.chart_generator.generate_weekly_chart(chart_data)
        self.chart_image = ft.Image(
            src_base64=chart_src.split(",")[1] if chart_src else "",
            width=500,
            height=300,
            border_radius=10
        )
    

    def _update_streak_display(self):
        current_streak, longest_streak = self.tracker.streak_manager.get_streak_data()
        self.streak_card.content.content.controls[1].value = f"Current: {current_streak} days"
        self.streak_card.content.content.controls[2].value = f"Best: {longest_streak} days"
        
        if current_streak >= 7:
            self.streak_card.color = "#E8F5E8"
            self.streak_card.content.content.controls[0].controls[0].color = ft.Colors.GREEN
        elif current_streak >= 3:
            self.streak_card.color = "#FFF8E1"
            self.streak_card.content.content.controls[0].controls[0].color = ft.Colors.AMBER
        else:
            self.streak_card.color = "#FFF3E0"
            self.streak_card.content.content.controls[0].controls[0].color = ft.Colors.ORANGE
    

    def _update_challenges_display(self):
        self.challenges_column.controls.clear()
        challenges = self.tracker.challenge_manager.get_challenges()
        
        for name, description, current, target, completed in challenges:
            card = self.data_manager.create_challenge_card(name, description, current, target, completed)
            self.challenges_column.controls.append(card)
    

    def _update_history_display(self):
        self.history_table.rows.clear()
        history = self.tracker.action_manager.get_action_history()
        
        for action, points, timestamp in history[:10]:  # Show last 10 actions
            row = self.data_manager.create_history_row(action, points, timestamp)
            self.history_table.rows.append(row)
    

    def _refresh_all_displays(self):
        self._update_history_display()
        self.total_points_text.value = f"Total Points: {self.tracker.points_manager.get_total_points()}"
        self._update_streak_display()
        self._update_challenges_display()
        
        chart_data = self.tracker.points_manager.get_points_per_day_last_week()
        new_chart_src = self.chart_generator.generate_weekly_chart(chart_data)
        if new_chart_src:
            self.chart_image.src_base64 = new_chart_src.split(",")[1]
    

    def _show_snackbar(self, page: ft.Page, message: str, color: str):
        page.snack_bar = ft.SnackBar(ft.Text(message), bgcolor=color)
        page.snack_bar.open = True
        page.update()
    

    def _log_action(self, e):
        selected = self.action_dropdown.value
        if not selected:
            self._show_snackbar(self.page, "⚠️ Please select an action before logging.", ft.Colors.ORANGE_300)
            return

        points = self.config.POINTS[selected]
        weekly_total = self.tracker.points_manager.get_weekly_points()

        if weekly_total + points > self.config.WEEKLY_CAP:
            self._show_snackbar(self.page, "🚫 Weekly point cap (1000 pts) reached!", ft.Colors.RED_300)
            return

        old_points = self.tracker.points_manager.get_total_points()
        
        success = self.tracker.log_action(selected, points)
        if not success:
            self._show_snackbar(self.page, "❌ Failed to log action!", ft.Colors.RED_300)
            return
        
        new_points = self.tracker.points_manager.get_total_points()
        
        self._refresh_all_displays()

        new_achievements = self.achievement_system.check_new_achievements(old_points, new_points)
        for milestone in new_achievements:
            achievement_widget = self.achievement_system.create_achievement_widget(milestone)
            self.achievements_column.controls.append(achievement_widget)

        current_streak, _ = self.tracker.streak_manager.get_streak_data()
        streak_msg = f" 🔥 {current_streak} day streak!" if current_streak > 1 else ""
        
        self._show_snackbar(self.page, f"✅ Logged '{selected}' for {points} points!{streak_msg}", 
                          ft.Colors.GREEN_300)


    def _reset_points(self, e):
        if not self.reset_stage["confirming"]:
            self.reset_button.text = "❗ Click again to confirm reset"
            self.reset_stage["confirming"] = True
            self.page.update()
            return

        success = self.tracker.reset_all_data()
        if success:
            self.history_table.rows.clear()
            self.total_points_text.value = f"Total Points: {self.tracker.points_manager.get_total_points()}"
            self.achievement_system.reset_achievements()
            self.achievements_column.controls.clear()
            self._update_streak_display()
            self._update_challenges_display()
            
            chart_data = self.tracker.points_manager.get_points_per_day_last_week()
            new_chart_src = self.chart_generator.generate_weekly_chart(chart_data)
            if new_chart_src:
                self.chart_image.src_base64 = new_chart_src.split(",")[1]
            
            self._show_snackbar(self.page, "✅ All data has been reset.", ft.Colors.BLUE_300)
        else:
            self._show_snackbar(self.page, "❌ Error resetting data.", ft.Colors.RED_300)

        self.reset_button.text = "🔄 Reset All Data"
        self.reset_stage["confirming"] = False
    
    def _create_main_layout(self) -> ft.Container:
        actions_tab = ft.Tab(
            text="🎯 Actions",
            content=ft.Container(
                content=ft.Column([
                    ft.Card(
                        content=ft.Container(
                            content=ft.Column([
                                self.action_dropdown,
                                self.log_button,
                                self.total_points_text,
                                self.streak_card
                            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=15),
                            padding=20
                        ),
                        elevation=5,
                        color=ft.Colors.WHITE
                    ),
                    ft.Text("📝 Recent Actions", size=18, weight="bold", color=ft.Colors.GREEN),
                    ft.Card(
                        content=ft.Container(
                            content=self.history_table,
                            padding=10
                        ),
                        elevation=3
                    ),
                    self.reset_button
                ], spacing=20),
                padding=20
            )
        )
        
        challenges_tab = ft.Tab(
            text="🏆 Challenges",
            content=ft.Container(
                content=ft.Column([
                    ft.Text("🎯 Active Challenges", size=20, weight="bold", color=ft.Colors.BLUE),
                    ft.Text("Complete challenges to earn special recognition!", 
                           size=14, color=ft.Colors.GREY_700),
                    self.challenges_column
                ], spacing=15),
                padding=20
            )
        )
        
        stats_tab = ft.Tab(
            text="📊 Stats",
            content=ft.Container(
                content=ft.Column([
                    ft.Text("🏆 Achievements", size=18, weight="bold", color=ft.Colors.ORANGE),
                    self.achievements_column,
                    ft.Divider(),
                    ft.Text("📊 Weekly Progress", size=18, weight="bold", color=ft.Colors.BLUE),
                    ft.Card(
                        content=ft.Container(
                            content=self.chart_image,
                            padding=15
                        ),
                        elevation=3
                    )
                ], spacing=15),
                padding=20
            )
        )
        
        tab_content = ft.Tabs(
            selected_index=0,
            animation_duration=300,
            tabs=[actions_tab, challenges_tab, stats_tab]
        )
        
        return ft.Container(
            content=ft.Column([
                ft.Container(
                    content=ft.Row([
                        ft.Icon("eco", color=ft.Colors.GREEN, size=40),
                        ft.Text("Round-2-Eco Tracker", size=28, weight="bold", color=ft.Colors.GREEN)
                    ], alignment=ft.MainAxisAlignment.CENTER),
                    bgcolor=ft.Colors.WHITE,
                    padding=20,
                    border_radius=10,
                    margin=ft.margin.only(bottom=20)
                ),
                tab_content
            ]),
            padding=0
        )
    
    def _load_initial_data(self):
        self._refresh_all_displays()
        
        total_points = self.tracker.points_manager.get_total_points()
        self.achievement_system.load_existing_achievements(total_points)
        
        for milestone in self.achievement_system.earned_achievements:
            achievement_widget = self.achievement_system.create_achievement_widget(milestone)
            self.achievements_column.controls.append(achievement_widget)
        
        self.page.update()
    
    def run(self, page: ft.Page):
        self.page = page
        
        page.title = "🌱 Round-2-Eco Tracker - Enhanced"
        page.theme_mode = ft.ThemeMode.LIGHT
        page.vertical_alignment = ft.MainAxisAlignment.START
        page.scroll = ft.ScrollMode.AUTO
        page.padding = 20
        page.bgcolor = self.config.THEME_COLORS["background"]
        
        main_container = self._create_main_layout()
        page.add(main_container)
        
        page.on_load = lambda _: self._load_initial_data()


def main(page: ft.Page):
    app = EcoTrackerApp()
    app.run(page)


class CustomEcoApp(EcoTrackerApp):
    
    def __init__(self):
        super().__init__()
        self.config.WEEKLY_CAP = 1000
        self.config.THEME_COLORS["primary"] = "#2196F3"


if __name__ == "__main__":
    app = EcoTrackerApp()
    ft.app(target=app.run, view=ft.AppView.FLET_APP)