# Pseudo code but here should be what the API does when it returns
# To the frontend when GET /api/v1/audit/review/{thread_id} is called.

# state_snapshot = await graph.get_state(config={"configurable": {"thread_id": thread_id}})
# anonymized_text = state_snapshot.values.get("anonymized_note")
# suggested_codes = state_snapshot.values.get("suggested_codes")


# Step 1, CrewAI finishes job, LangGraph saves into SQliteSaver db, interrupt_before
# Step 2, Frontend GET with thread_id to FastAPI
# Step 3, using thread_id, FastAPI gets all info for frontend display
# Step 4, returns it to the frontend for approval
# Step 5, once signed-off, frontend sends only approved disease codes
# Step 6, LangGraph restarts with the pseudo code below

# await graph.update_state(
#     config={"configurable": {"thread_id": thread_id}},
#     values={"approved_codes": payload.approved_codes},
#     as_node="human_audit_gatekeeper"
# )
# # Resume execution path safely
# await graph.stream(None, config={"configurable": {"thread_id": thread_id}})
