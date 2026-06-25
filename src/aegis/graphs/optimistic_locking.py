from langgraph.errors import CheckpointNotLatest  # or equivalent exception


def handle_human_approval(case_id, checkpoint_id, new_state):
    try:
        config = {"configurable": {"thread_id": case_id, "checkpoint_id": checkpoint_id}}
        app.update_state(config, new_state)
    except CheckpointNotLatest:
        # This is where you trigger your 409 conflict error
        raise HTTPException(
            status_code=409,
            detail="The state has changed since you last fetched it. Please refresh.",
        )
