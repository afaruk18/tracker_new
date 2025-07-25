from tracker.db.query_store import QueryStore

QueryStore.save_query(
    name="Last shutdown(logout) time",
    query=(
        "What is last shutdown(logout) time?"
    ),
    tags=["lsd"],
)

