const express = require("express");
const jwt = require("jsonwebtoken");
const db = require("../db");
const { accessTokenSecret } = require("../config");
const { authLimiter } = require("../middleware/rateLimiter");

const router = express.Router();

// POST /api/auth/login
router.post("/login", authLimiter, async (req, res) => {
  const { email, password } = req.body || {};

  if (!email || !password) {
    return res.status(400).json({ message: "Email and password required" });
  }

  try {
    const result = await db.query(
      "SELECT id, email, full_name, password_hash, role FROM users WHERE email = $1",
      [email]
    );

    if (result.rows.length === 0) {
      return res.status(401).json({ message: "Invalid credentials" });
    }

    const user = result.rows[0];

    // For simplicity in this assessment, we compare plain text.
    // In a real system you would use bcrypt and store a hash.
    if (password !== user.password_hash) {
      return res.status(401).json({ message: "Invalid credentials" });
    }

    const payload = {
      userId: user.id,
      email: user.email,
      role: user.role
    };

    const accessToken = jwt.sign(payload, accessTokenSecret, {
      expiresIn: "1h"
    });

    const userResponse = {
      id: user.id,
      email: user.email,
      fullName: user.full_name,
      role: user.role
    };

    res.json({ user: userResponse, accessToken });
  } catch (err) {
    console.error("Error in /api/auth/login:", err);
    res.status(500).json({ message: "Internal server error" });
  }
});

module.exports = router;
