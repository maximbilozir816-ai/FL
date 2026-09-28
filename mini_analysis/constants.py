"""Callback-data strings and FSM state keys for the free mini-analysis flow.

All keys are prefixed with `mini_` / named distinctly from the ones used in
handlers/photo.py (`rejection_count`, `skip_check`, `skip_msg_id`) so the two
flows can never collide inside the same FSMContext storage.
"""

CB_GET_MINI_ANALYSIS = "get_mini_analysis"
CB_SKIP_MINI_QUALITY_CHECK = "skip_mini_quality_check"

STATE_KEY_AWAITING_MINI_PHOTO = "awaiting_mini_photo"
STATE_KEY_MINI_REJECTION_COUNT = "mini_rejection_count"
STATE_KEY_MINI_SKIP_CHECK = "mini_skip_check"
STATE_KEY_MINI_SKIP_MSG_ID = "mini_skip_msg_id"
STATE_KEY_MINI_INSTRUCTION_MSG_ID = "mini_instruction_msg_id"
