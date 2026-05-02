from up_police_ai.db.models import PlanDayRow
from up_police_ai.data.tasks import AREA_NAMES

LEVEL_NAMES = {"B": "Beginner", "I": "Intermediate", "V": "Advanced"}
AREA_SEQUENCE = ["A", "B", "C", "D"]
AREA_FULL_NAMES = {
    "A": AREA_NAMES["A"],
    "B": AREA_NAMES["B"],
    "C": AREA_NAMES["C"],
    "D": AREA_NAMES["D"],
}


def get_level_code(avg: float) -> str:
    if avg < 2.5:
        return "B"
    if avg < 3.75:
        return "I"
    return "V"


def generate_plan_days(
    plan_id: str,
    avg_a: float,
    avg_b: float,
    avg_c: float,
    avg_d: float,
) -> list[PlanDayRow]:
    avgs = {"A": avg_a, "B": avg_b, "C": avg_c, "D": avg_d}
    level_codes = {area: get_level_code(avg) for area, avg in avgs.items()}
    days = []
    for day_num in range(1, 31):
        area = AREA_SEQUENCE[(day_num - 1) % 4]
        occurrence = (day_num - 1) // 4
        task_idx = occurrence % 5
        level_code = level_codes[area]
        task_key = f"{area}_{level_code}_{task_idx}"
        days.append(
            PlanDayRow(
                plan_id=plan_id,
                day_number=day_num,
                focus_area=AREA_FULL_NAMES[area],
                level=LEVEL_NAMES[level_code],
                task_key=task_key,
                status="not_started",
            )
        )
    return days
