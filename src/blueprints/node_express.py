"""Node.js & Express REST API Golden Blueprint (docs/01 §8, docs/08).

Generates production-grade Express REST API with routing, middleware,
environment configuration, Dockerfile, docker-compose, and test suite.
"""
from pathlib import Path

from src.blueprints.base import Blueprint
from src.models.enums import TargetType
from src.models.project import ProjectSpec
from src.workspace.workspace import Workspace


class NodeExpressBlueprint(Blueprint):
    """Production-grade Node.js & Express REST API Blueprint."""

    @property
    def name(self) -> str:
        return "node_express"

    @property
    def targets(self) -> list[TargetType]:
        return [TargetType.API, TargetType.WEB]

    def generate_scaffold(self, workspace: Workspace, spec: ProjectSpec) -> list[Path]:
        workspace.ensure_directories()
        slug = spec.name.lower().replace(" ", "-").replace("_", "-")
        backend_dir = workspace.backend_dir
        src_dir = backend_dir / "src"
        routes_dir = src_dir / "routes"
        routes_dir.mkdir(parents=True, exist_ok=True)

        generated_paths = []

        # 1. package.json
        pkg_path = backend_dir / "package.json"
        pkg_path.write_text(
            f'''{{
  "name": "{slug}",
  "version": "1.0.0",
  "description": "Generated autonomously by Prompt2Product",
  "main": "src/server.js",
  "scripts": {{
    "start": "node src/server.js",
    "dev": "nodemon src/server.js",
    "test": "jest"
  }},
  "dependencies": {{
    "express": "^4.19.2",
    "cors": "^2.8.5",
    "dotenv": "^16.4.5"
  }},
  "devDependencies": {{
    "jest": "^29.7.0",
    "supertest": "^6.3.4"
  }}
}}
''',
            encoding="utf-8",
        )
        generated_paths.append(pkg_path)

        # 2. src/server.js
        server_path = src_dir / "server.js"
        server_path.write_text(
            f'''require("dotenv").config();
const express = require("express");
const cors = require("cors");
const itemsRouter = require("./routes/items");

const app = express();
const PORT = process.env.PORT || 5000;

app.use(cors());
app.use(express.json());

// Health Check Endpoint
app.get("/health", (req, res) => {{
  res.json({{ status: "ok", project: "{spec.name}", timestamp: new Date().toISOString() }});
}});

// API Routes
app.use("/api/items", itemsRouter);

if (process.env.NODE_ENV !== "test") {{
  app.listen(PORT, () => {{
    console.log(`{spec.name} API server running on port ${{PORT}}`);
  }});
}}

module.exports = app;
''',
            encoding="utf-8",
        )
        generated_paths.append(server_path)

        # 3. src/routes/items.js
        items_path = routes_dir / "items.js"
        items_path.write_text(
            '''const express = require("express");
const router = express.Router();

let items = [
  { id: 1, title: "Initial Task", completed: false }
];

router.get("/", (req, res) => {
  res.json({ items });
});

router.post("/", (req, res) => {
  const { title } = req.body;
  if (!title) {
    return res.status(400).json({ error: "Title is required" });
  }
  const newItem = { id: items.length + 1, title, completed: false };
  items.push(newItem);
  res.status(201).json(newItem);
});

module.exports = router;
''',
            encoding="utf-8",
        )
        generated_paths.append(items_path)

        # 4. README.md
        readme_path = backend_dir / "README.md"
        readme_path.write_text(
            f'''# {spec.name} (Node.js & Express REST API)

Scaffolded autonomously by Prompt2Product.

## Quick Start
```bash
npm install
npm start
```
Server runs on [http://localhost:5000](http://localhost:5000).
Check health: `GET /health`
''',
            encoding="utf-8",
        )
        generated_paths.append(readme_path)

        return generated_paths

    def generate_infra(self, workspace: Workspace, spec: ProjectSpec) -> list[Path]:
        workspace.ensure_directories()
        backend_dir = workspace.backend_dir
        generated_paths = []

        # 1. Dockerfile
        dockerfile_path = backend_dir / "Dockerfile"
        dockerfile_path.write_text(
            '''FROM node:18-alpine
WORKDIR /app
COPY package.json ./
RUN npm install --production
COPY . .
EXPOSE 5000
CMD ["npm", "start"]
''',
            encoding="utf-8",
        )
        generated_paths.append(dockerfile_path)

        # 2. docker-compose.yml
        compose_path = backend_dir / "docker-compose.yml"
        compose_path.write_text(
            '''version: "3.8"

services:
  api:
    build: .
    ports:
      - "5000:5000"
    environment:
      - PORT=5000
      - NODE_ENV=production
''',
            encoding="utf-8",
        )
        generated_paths.append(compose_path)

        return generated_paths

    def generate_tests(self, workspace: Workspace, spec: ProjectSpec) -> list[Path]:
        workspace.ensure_directories()
        tests_dir = workspace.backend_dir / "tests"
        tests_dir.mkdir(parents=True, exist_ok=True)
        generated_paths = []

        test_path = tests_dir / "api.test.js"
        test_path.write_text(
            f'''const request = require("supertest");
const app = require("../src/server");

describe("{spec.name} Express API Suite", () => {{
  test("GET /health returns 200 and ok status", async () => {{
    const res = await request(app).get("/health");
    expect(res.statusCode).toBe(200);
    expect(res.body.status).toBe("ok");
  }});
}});
''',
            encoding="utf-8",
        )
        generated_paths.append(test_path)
        return generated_paths
