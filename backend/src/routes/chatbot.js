const express = require("express");
const jwt = require("jsonwebtoken");
const { authenticateAccessToken } = require("../middleware/auth");
const { chatTokenSecret } = require("../config");
const { authLimiter } = require("../middleware/rateLimiter");

const router = express.Router();

// POST /api/chatbot/token
router.post("/token", authenticateAccessToken, authLimiter, (req, res) => {
  const user = req.user;

  const payload = {
    userId: user.userId,
    email: user.email
  };

  const chatToken = jwt.sign(payload, chatTokenSecret, {
    expiresIn: "5m" // short-lived token
  });

  res.json({ chatToken });
});

module.exports = router;
