import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__)))
from routers.questions import format_question

test_row = {
    "id": "moubbxtq",
    "subject": "Physics",
    "chapter": "electrostatics",
    "year": 2023,
    "paper": "NEET",
    "question_text": "In the circuit shown below",
    "options": '{"A": "extracted_images/moubbxtq_A.png", "B": "extracted_images/moubbxtq_B.png"}',
    "correct_answer": "A",
    "solution": "Solution text",
    "image_path": "examside_data/images/moubbxtq.png",
    "solution_image_path": None,
    "data_quality": "good",
    "options_image": "moubbxtq_opt.png"
}

formatted = format_question(test_row)
print("OPTIONS_IMAGE_URL:", formatted["options_image_url"])
print("OPTIONS:", formatted["options"])
