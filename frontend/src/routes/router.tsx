import { createBrowserRouter, Navigate } from "react-router-dom";
import { AppLayout } from "../components/AppLayout";
import { ClinicalSubmissionPage } from "../features/clinical-submission/ClinicalSubmissionPage";
import { DecisionDetailPage } from "../features/decision-detail/DecisionDetailPage";
import { ReviewQueuePage } from "../features/review-queue/ReviewQueuePage";
import { DashboardPage } from "./DashboardPage";
import { NotFoundPage } from "./NotFoundPage";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <AppLayout />,
    children: [
      { index: true, element: <Navigate to="/dashboard" replace /> },
      { path: "dashboard", element: <DashboardPage /> },
      { path: "submit", element: <ClinicalSubmissionPage /> },
      { path: "reviews", element: <ReviewQueuePage /> },
      { path: "reviews/:threadId", element: <DecisionDetailPage /> },
      { path: "*", element: <NotFoundPage /> },
    ],
  },
]);
