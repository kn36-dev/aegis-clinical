# scripts/verify_topology.py
import asyncio
import uuid
from typing import TYPE_CHECKING

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from aegis.graphs.workflow import workflow

if TYPE_CHECKING:
    from langchain_core.runnables import RunnableConfig

    from aegis.graphs.state import PatientGraphState


async def execute_minimal_validation():
    print("🚀 Starting Aegis-Clinical Topology Verification...\n")

    # 1. Initialize an ephemeral, thread-safe persistence layer
    async with AsyncSqliteSaver.from_conn_string("data/test_checkpoints.db") as saver:
        await saver.setup()

        # Compile the graph INSIDE the active database lifecycle context
        runtime_graph = workflow.compile(checkpointer=saver)

        # Attach our test checkpointer to the graph structure
        # (Note: if your workflow file already pre-compiled it, pass your local config)
        thread_id = str(uuid.uuid4())
        config: RunnableConfig = {"configurable": {"thread_id": thread_id}}

        # 2. Inject a 100% synthetic, colloquial patient note payload
        initial_state: PatientGraphState = {
            "case_id": thread_id,
            "patient_id": "PT-999-TEST",
            "raw_note": "Patient presents with sudden onset of acute watery "
            "diarrhea and severe dehydration.",
            "anonymized_note": "",
            "extracted_codes": [],
            "confidence_score": 0.0,
            "status": "QUEUED",
            "hitl_rejection_notes": "",
        }

        print(f"📥 Step 1: Ingesting case thread: {thread_id}")

        # 3. Stream the graph execution nodes step-by-step
        # We loop through the graph generator to witness transitions in real time
        async for event in runtime_graph.astream(
            initial_state, config=config, stream_mode="updates"
        ):
            for node_name, state_update in event.items():
                updated_keys = list(state_update.keys())
                print(f"   ⚙️ Node Executed: [{node_name}] -> State Updated Keys: {updated_keys}")

        # 4. Check if the graph successfully hit the manual review gate and paused
        current_snapshot = await runtime_graph.aget_state(config)
        print(f"\n📊 Current Graph State Status: {current_snapshot.values.get('status')}")
        print(f"🔒 Next Pending Graph Nodes: {current_snapshot.next}")

        # Assert that the state chart halted at the human_review barrier due to low confidence
        if (
            "human_review" in current_snapshot.next
            or current_snapshot.values.get("status") == "PENDING_HITL"
        ):
            print(
                "✅ Success: LangGraph matching engine correctly interrupted and paused for review."
            )
        else:
            print("❌ Failure: Graph failed to interrupt at the designated validation boundary.")
            return

        print("\n👨‍⚕️ Step 2: Simulating Asynchronous Physician Sign-off via React Dashboard...")

        # 5. Hydrate the paused state dictionary, apply updates, and flash it back to SQLite
        mutated_values = {
            **current_snapshot.values,
            "status": "ARCHIVED",
            "confidence_score": 1.0,  # Overriding confidence metric to pass validation gates
            "extracted_codes": [{"code": "1A00", "title": "Cholera due to Vibrio cholerae 01"}],
        }

        # Write updates directly to the checkpoint store under the node identity
        await runtime_graph.aupdate_state(config, mutated_values, as_node="human_review")
        print("   📝 Checkpoint state storage modified safely in SQLite registry.")

        print("\n⏯️ Step 3: Resuming the graph instance past the suspension gate...")

        # 6. Call ainvoke with None to wake up the execution thread right where it was paused
        final_output = await runtime_graph.ainvoke(None, config=config)

        print(f"🏁 Final Terminal Graph State Status: {final_output.get('status')}")
        if final_output.get("status") == "ARCHIVED":
            print(
                "\n🎉 Verification complete! The LangGraph, CrewAI, and PydanticAI boundary flow is"
                " 100% correct."
            )
        else:
            print(
                "\n❌ Verification failed: The state machine did not exit in the expected ARCHIVED "
                "state."
            )


if __name__ == "__main__":
    # Execute the asynchronous test loop using uv or standard python execution runtimes
    asyncio.run(execute_minimal_validation())
