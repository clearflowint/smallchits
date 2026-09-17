# Tech Stack
- **Vue 3**: Progressive JavaScript frontend framework using the Composition API (`<script setup>`).
- **Vite**: Fast modern frontend bundler and development server configuring PWA and proxying.
- **Tailwind CSS & PostCSS**: Utility-first styling framework with custom brand colors (`clearflow-slate`, `clearflow-blue`, `clearflow-surplus`, `clearflow-deficit`, `clearflow-pending`).
- **Vue Router**: Client-side single page application routing configured in `frontend/src/router/index.js`.
- **Pinia**: Lightweight, reactive state management store for Vue.
- **Axios**: Promise-based HTTP client pre-configured with auth interceptors in `frontend/src/composables/useApi.js`.
- **FastAPI (Python 3.12)**: High-performance backend REST API with Pydantic validation and modular routers.
- **NocoDB**: No-code relational database API layer accessed via `backend/app/core/nocodb_client.py`.
- **n8n**: Workflow automation engine executing scheduled crons (D-2 reminder, D+10 overdue, D+20 statements).
- **vite-plugin-pwa**: Progressive Web App plugin providing service worker lifecycle and web app manifest.

---

# Library & Architecture Rules

### 1. Frontend UI & Component Structure
- **Vue 3 (`vue`)**: Use the Composition API with `<script setup>` syntax for all components and views.
- **Views vs Components**:
  - Full-screen route pages belong in `frontend/src/views/` (e.g., `HomeView.vue`, `SummaryView.vue`, `LoginView.vue`, `OnboardingView.vue`).
  - Reusable modular UI widgets belong in `frontend/src/components/` (e.g., `ShareCard.vue`, `PaymentDrawer.vue`, `DrawControl.vue`).
- **Routing (`vue-router`)**: Define all application routes in `frontend/src/router/index.js`. Use lazy imports (`() => import(...)`) for views.

### 2. State & API Communication
- **State Management (`pinia` & Vue Composables)**:
  - Global reactive shared state should use Pinia stores or composables in `frontend/src/composables/` (e.g., `useAuth.js`, `useApi.js`).
  - Component-local state must use standard Vue primitives (`ref`, `computed`, `reactive`).
- **HTTP Client (`axios`)**:
  - Always communicate with the backend through the central `useApi` composable (`frontend/src/composables/useApi.js`).
  - Do not create independent raw Axios instances; use `useApi()` to ensure consistent `/api` baseURL and 401 redirect handling.

### 3. Styling & Design System
- **Tailwind CSS (`tailwindcss`)**:
  - Style all components using Tailwind utility classes.
  - Follow the ClearFlow brand color palette defined in `frontend/tailwind.config.js`:
    - `bg-clearflow-slate` for background surfaces (#0F172A).
    - `text-clearflow-blue` / `bg-clearflow-blue` for primary brand accents (#2563EB).
    - `text-clearflow-surplus` (#16A34A) and `text-clearflow-deficit` (#DC2626) for financial indicators.
    - `text-clearflow-pending` (#F59E0B) for pending status.
  - Avoid inline CSS styles unless calculating dynamic dimensions or positions.

### 4. Backend Service & Data Layer
- **FastAPI & Pydantic**:
  - Route handlers live in `backend/app/routers/` separated by domain (`auth`, `chittis`, `shares`, `dashboard`, `onboarding`, `whatsapp`, `drive`).
  - Domain models and schema validations belong in `backend/app/models.py`.
  - Financial calculations and core business logic belong in `backend/app/services/` (e.g., `chitti_math_engine.py`, `cycle_service.py`).
- **NocoDB Client**:
  - Direct database queries must go through `NocoDBClient` in `backend/app/core/nocodb_client.py`.

### 5. Background Automations
- **n8n**:
  - Background workflows, scheduled notifications, and WhatsApp alerts are managed via workflow JSON definitions in `n8n/workflows/`.
