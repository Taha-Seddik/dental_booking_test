const app = require("./app");
const { port } = require("./config");
const db = require("./db");

async function start() {
  try {
    await db.query("SELECT 1");
    console.log("Connected to PostgreSQL");
  } catch (err) {
    console.error("Failed to connect to PostgreSQL:", err);
  }

  app.listen(port, () => {
    console.log(`Backend API listening on port ${port}`);
  });
}

start();
