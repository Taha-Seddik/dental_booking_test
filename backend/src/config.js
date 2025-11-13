const dotenv = require("dotenv");
dotenv.config();

module.exports = {
  port: process.env.PORT || 4000,
  db: {
    host: process.env.DB_HOST || "localhost",
    port: parseInt(process.env.DB_PORT || "5432", 10),
    user: process.env.DB_USER || "postgres",
    password: process.env.DB_PASSWORD || "postgres",
    database: process.env.DB_NAME || "dental_chatbot"
  },
  accessTokenSecret: process.env.ACCESS_TOKEN_SECRET || "dev_access_secret",
  chatTokenSecret: process.env.CHAT_TOKEN_SECRET || "dev_chat_secret",
  pythonServiceUrl: process.env.PYTHON_SERVICE_URL || "http://python-service:8000"
};
