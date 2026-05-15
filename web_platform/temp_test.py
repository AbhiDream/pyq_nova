import sys
sys.path.insert(0, '.')
try:
    from routers.questions import serialize_row
except ImportError:
    from questions import serialize_row

fake_row = {
    'id': 'test',
    'subject': 'Chemistry',
    'chapter': 'Test',
    'year': 2022,
    'difficulty': 'medium',
    'question_text': 'Match the reagents\nList-I\nList-II\n(a)\nZero order\n(i)\nBenzene',
    'image_path': None,
    'options': '{"A": "opt1"}',
    'correct_answer': 'A',
    'explanation': '',
    'tags': []
}
result = serialize_row(fake_row)
print(repr(result.get('question_text', '')))
print('---')
print(repr(result.get('match_list_parsed', '')))
