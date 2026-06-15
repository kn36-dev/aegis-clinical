// Core logic: Axios instance configured with a base URL matching FastAPI server.
// Payload Mappings: 2 methods:
// - getPendingReviews(): active list of LangGraph thread checkpoints
// - submitReview(token: string, payload: ICD11Payload): sends the physician adjustments and the resume_token back to review.py router