-- SAMPLE USERS
INSERT INTO users (email, password_hash, full_name, role)
VALUES 
('alice@example.com', 'hashed_password_1', 'Alice Patient', 'patient'),
('dr.bob@example.com', 'hashed_password_2', 'Dr. Bob Dentist', 'dentist')
ON CONFLICT (email) DO NOTHING;

-- SAMPLE CHAT SESSION
INSERT INTO chat_sessions (user_id, status, metadata)
VALUES
(
  (SELECT id FROM users WHERE email = 'alice@example.com'),
  'active',
  '{"channel": "web", "browser": "Chrome"}'
);

-- SAMPLE APPOINTMENTS
INSERT INTO appointments (
  user_id,
  chat_session_id,
  start_time,
  end_time,
  status,
  notes,
  provider_name,
  location
)
VALUES
(
  (SELECT id FROM users WHERE email = 'alice@example.com'),
  (SELECT id FROM chat_sessions WHERE user_id = (SELECT id FROM users WHERE email = 'alice@example.com') ORDER BY started_at LIMIT 1),
  NOW() + INTERVAL '1 day',
  NOW() + INTERVAL '1 day 30 minutes',
  'confirmed',
  'Routine dental cleaning',
  'Dr. Bob Dentist',
  'Downtown Dental Clinic'
),
(
  (SELECT id FROM users WHERE email = 'alice@example.com'),
  NULL,
  NOW() + INTERVAL '7 days',
  NOW() + INTERVAL '7 days 30 minutes',
  'pending',
  'Follow-up check',
  'Dr. Bob Dentist',
  'Downtown Dental Clinic'
);
