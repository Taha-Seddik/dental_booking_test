const jwt = require("jsonwebtoken");
const { accessTokenSecret, chatTokenSecret } = require("../config");

function authenticateAccessToken(req, res, next) {
  const authHeader = req.headers["authorization"];
  const token = authHeader && authHeader.split(" ")[1];

  if (!token) {
    return res.status(401).json({ message: "Missing access token" });
  }

  jwt.verify(token, accessTokenSecret, (err, user) => {
    if (err) {
      return res.status(403).json({ message: "Invalid or expired access token" });
    }
    req.user = user;
    next();
  });
}

function authenticateChatToken(req, res, next) {
  const authHeader = req.headers["authorization"];
  const token = authHeader && authHeader.split(" ")[1];

  if (!token) {
    return res.status(401).json({ message: "Missing chat token" });
  }

  jwt.verify(token, chatTokenSecret, (err, payload) => {
    if (err) {
      return res.status(403).json({ message: "Invalid or expired chat token" });
    }
    req.chatUser = payload;
    next();
  });
}

module.exports = {
  authenticateAccessToken,
  authenticateChatToken,
};
