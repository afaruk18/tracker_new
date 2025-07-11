from tracker.db.query_store import QueryStore

QueryStore.save_query(
    name="Total Useful Activity time",
    query=(
        "What is useful activity time?"
    ),
    tags=["act"],
)