const express = require("express");
const axios = require("axios");
const db = require("../db");
const { authenticateChatToken } = require("../middleware/auth");
const { chatLimiter } = require("../middleware/rateLimiter");
const { pythonServiceUrl } = require("../config");

const router = express.Router();

// Helper to create a new chat session
async function createChatSession(userId) {
  const result = await db.query(
    "INSERT INTO chat_sessions (user_id, status, started_at, last_message_at, metadata) VALUES ($1, 'active', NOW(), NOW(), $2) RETURNING id",
    [userId, { channel: "web" }]
  );
  return result.rows[0].id;
}

// POST /api/chat
router.post("/", authenticateChatToken, chatLimiter, async (req, res) => {
  const { message, sessionId: clientSessionId, userId: bodyUserId } = req.body || {};
  const authUserId = req.chatUser?.userId;

  if (!message || typeof message !== "string") {
    return res.status(400).json({ message: "message is required" });
  }

  const userId = bodyUserId || authUserId;

  if (!userId) {
    return res.status(400).json({ message: "userId is missing" });
  }

  let sessionId = clientSessionId;

  try {
    if (!sessionId) {
      sessionId = await createChatSession(userId);
    }

    let replyText = "";

    // Try to call Python microservice if available
    try {

      const response = await axios.post(`${pythonServiceUrl}/chat`, {
        userId,
        sessionId,
        message,
      });

      replyText = response.data.reply || "I have processed your request.";
      if (response.data.sessionId && response.data.sessionId !== sessionId) {
        sessionId = response.data.sessionId;
      }
    } catch (err) {
      const msg = err.response
        ? `HTTP ${err.response.status} ${err.response.statusText} from ${pythonServiceUrl}/chat`
        : err.code
        ? `${err.code} to ${pythonServiceUrl}/chat`
        : err.message || "Unknown error";
      console.warn("Python service not available, falling back to simple reply:", msg);
      replyText =
        "Thanks for your message. This is a placeholder reply until the LangChain service is connected.\n\nYou said: " +
        message;
    }

    await db.query("UPDATE chat_sessions SET last_message_at = NOW() WHERE id = $1", [sessionId]);

    res.json({
      reply: replyText,
      sessionId,
    });
  } catch (err) {
    console.error("Error in /api/chat:", err);
    res.status(500).json({ message: "Internal server error" });
  }
});

module.exports = router;
