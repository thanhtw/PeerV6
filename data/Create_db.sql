
-- Enhanced Database Schema for Java Peer Review Training System
-- Version: 2.0 with Comprehensive Logging and Badge System
-- New Datatable
SET FOREIGN_KEY_CHECKS = 0;
DROP VIEW IF EXISTS user_performance_summary;
DROP VIEW IF EXISTS daily_activity_summary;
DROP VIEW IF EXISTS badge_progress_summary; 

DROP VIEW IF EXISTS user_practice_summary; 

DROP TABLE IF EXISTS user_badges;
DROP TABLE IF EXISTS activity_log;
DROP TABLE IF EXISTS java_errors;
DROP TABLE IF EXISTS error_categories;
DROP TABLE IF EXISTS badges;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS user_sessions;
DROP TABLE IF EXISTS user_interactions;
DROP TABLE IF EXISTS error_category_stats;
DROP TABLE IF EXISTS review_sessions;
DROP TABLE IF EXISTS badge_progress;
DROP TABLE IF EXISTS user_streaks;  
SET FOREIGN_KEY_CHECKS = 1;


-- Create users table
CREATE TABLE IF NOT EXISTS users (
    uid VARCHAR(36) PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL, 
    password VARCHAR(255) NOT NULL,      
    display_name_en VARCHAR(255),
    display_name_zh VARCHAR(255),
    level_name_en VARCHAR(50) DEFAULT 'Basic',
    level_name_zh VARCHAR(50) DEFAULT '基礎',   
    reviews_completed INT DEFAULT 0,
    score INT DEFAULT 0,
    total_points INT DEFAULT 0,
    consecutive_days INT DEFAULT 0,
    last_activity DATE DEFAULT NULL,
    total_session_time INT DEFAULT 0,
    preferred_language ENUM('en', 'zh') DEFAULT 'en',
    perfect_reviews_count INT DEFAULT 0,
    average_accuracy DECIMAL(5,2) DEFAULT 0.00,
    last_badge_check TIMESTAMP NULL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    INDEX idx_email (email),
    INDEX idx_level (level_name_en),
    INDEX idx_points (total_points DESC),
    INDEX idx_activity (last_activity DESC),
    INDEX idx_performance (reviews_completed, score),
    INDEX idx_users_performance (average_accuracy DESC, perfect_reviews_count DESC),
    INDEX idx_users_badge_check (last_badge_check ASC)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Badges table
CREATE TABLE IF NOT EXISTS badges (
    badge_id VARCHAR(50) PRIMARY KEY,
    name_en VARCHAR(100) NOT NULL,
    name_zh VARCHAR(100) NOT NULL,
    description_en TEXT NOT NULL,
    description_zh TEXT NOT NULL,
    icon VARCHAR(50) DEFAULT '🏅',
    category ENUM('achievement', 'progress', 'skill', 'consistency', 'special') DEFAULT 'achievement',
    difficulty ENUM('easy', 'medium', 'hard', 'legendary') DEFAULT 'medium',
    points INT DEFAULT 10,
    rarity ENUM('common', 'uncommon', 'rare', 'epic', 'legendary') DEFAULT 'common',
    prerequisite_badges JSON, 
    criteria JSON NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_category (category),
    INDEX idx_difficulty (difficulty),
    INDEX idx_rarity (rarity),
    INDEX idx_active (is_active)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- User Sessions - Track overall user sessions
-- Add error_category_stats table (referenced in code but missing from schema)
CREATE TABLE IF NOT EXISTS error_category_stats (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    category_name VARCHAR(100) NOT NULL,
    encountered INT DEFAULT 0,
    identified INT DEFAULT 0,
    mastery_level DECIMAL(5,2) DEFAULT 0.00,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(uid) ON DELETE CASCADE,
    UNIQUE KEY unique_user_category (user_id, category_name),
    INDEX idx_user_mastery (user_id, mastery_level DESC),
    INDEX idx_category_performance (category_name, mastery_level DESC)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Add review_sessions table for detailed session tracking
CREATE TABLE IF NOT EXISTS review_sessions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(500) NOT NULL,
    session_id VARCHAR(500) NOT NULL,
    code_difficulty VARCHAR(20) DEFAULT 'medium',
    total_errors INT DEFAULT 0,
    identified_errors INT DEFAULT 0,
    accuracy_percentage DECIMAL(5,2) DEFAULT 0.00,
    review_iterations INT DEFAULT 1,
    time_spent_seconds INT DEFAULT 0,
    session_type ENUM('practice', 'regular', 'tutorial') DEFAULT 'regular',
    practice_error_code VARCHAR(100) NULL,
    completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(uid) ON DELETE CASCADE,
    INDEX idx_user_performance (user_id, accuracy_percentage DESC, completed_at DESC),
    INDEX idx_session_stats (session_type, accuracy_percentage DESC),
    INDEX idx_practice_tracking (user_id, practice_error_code, completed_at DESC)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;


CREATE TABLE IF NOT EXISTS user_error_practice (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    error_code VARCHAR(100) NOT NULL,
    error_name_en VARCHAR(200) NOT NULL,
    error_name_zh VARCHAR(200) NOT NULL,
    category_name VARCHAR(100) NOT NULL,
    practice_count INT DEFAULT 0,
    total_attempts INT DEFAULT 0,
    successful_completions INT DEFAULT 0,
    best_accuracy DECIMAL(5,2) DEFAULT 0.00,
    total_time_spent INT DEFAULT 0,
    last_practiced TIMESTAMP NULL,
    first_practiced TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completion_status ENUM('not_started', 'in_progress', 'completed', 'mastered') DEFAULT 'not_started',
    mastery_level DECIMAL(5,2) DEFAULT 0.00,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(uid) ON DELETE CASCADE,
    UNIQUE KEY unique_user_error (user_id, error_code),
    INDEX idx_user_practice (user_id, completion_status),
    INDEX idx_error_practice (error_code, completion_status),
    INDEX idx_user_mastery (user_id, mastery_level DESC),
    INDEX idx_practice_stats (user_id, last_practiced DESC)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;


-- Add badge_progress table to track incremental progress toward badges
CREATE TABLE IF NOT EXISTS badge_progress (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    badge_id VARCHAR(50) NOT NULL,
    current_progress INT DEFAULT 0,
    target_progress INT DEFAULT 0,
    progress_data JSON,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(uid) ON DELETE CASCADE,
    FOREIGN KEY (badge_id) REFERENCES badges(badge_id) ON DELETE CASCADE,
    UNIQUE KEY unique_user_badge_progress (user_id, badge_id),
    INDEX idx_progress_tracking (user_id, current_progress, target_progress)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Add user_streaks table for consistency tracking
CREATE TABLE IF NOT EXISTS user_streaks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    streak_type VARCHAR(50) NOT NULL,
    current_streak INT DEFAULT 0,
    longest_streak INT DEFAULT 0,
    last_activity_date DATE,
    streak_data JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(uid) ON DELETE CASCADE,
    UNIQUE KEY unique_user_streak_type (user_id, streak_type),
    INDEX idx_streak_tracking (user_id, streak_type, current_streak DESC)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Error categories table
CREATE TABLE error_categories (
    id INT AUTO_INCREMENT PRIMARY KEY,    
    name_en VARCHAR(100) NOT NULL,
    name_zh VARCHAR(100) NOT NULL,
    description_en TEXT,
    description_zh TEXT,
    icon VARCHAR(50) DEFAULT '📂',
    sort_order INT DEFAULT 0,    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_name_en (name_en),
    INDEX idx_sort_order (sort_order)    
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Java errors table
CREATE TABLE java_errors (
    id INT AUTO_INCREMENT PRIMARY KEY,
    error_code VARCHAR(100) NOT NULL UNIQUE,
    category_id INT NOT NULL,
    error_name_en VARCHAR(200) NOT NULL,
    error_name_zh VARCHAR(200) NOT NULL,
    description_en TEXT NOT NULL,
    description_zh TEXT NOT NULL,
    implementation_guide_en TEXT, 
    implementation_guide_zh TEXT,
    difficulty_level ENUM('easy', 'medium', 'hard') DEFAULT 'medium',
    frequency_weight INT DEFAULT 1,
    tags JSON,
    examples JSON,    
    usage_count INT DEFAULT 0,
    success_rate DECIMAL(5,2) DEFAULT 0.00,
    avg_identification_time INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (category_id) REFERENCES error_categories(id) ON DELETE CASCADE,
    INDEX idx_error_code (error_code),
    INDEX idx_category_difficulty (category_id, difficulty_level),
    INDEX idx_usage_stats (usage_count, success_rate)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- User badges table
CREATE TABLE user_badges (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    badge_id VARCHAR(50) NOT NULL,
    awarded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    progress_data JSON,
    notification_sent BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (user_id) REFERENCES users(uid) ON DELETE CASCADE,
    FOREIGN KEY (badge_id) REFERENCES badges(badge_id) ON DELETE CASCADE,
    UNIQUE KEY unique_user_badge (user_id, badge_id),
    INDEX idx_user_awarded (user_id, awarded_at DESC),
    INDEX idx_badge_awarded (badge_id, awarded_at DESC)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Activity log table
CREATE TABLE activity_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    activity_type VARCHAR(50) NOT NULL,
    points INT NOT NULL,
    details_en TEXT,
    details_zh TEXT,
    metadata JSON,
    related_entity_type VARCHAR(50),
    related_entity_id VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(uid) ON DELETE CASCADE,
    INDEX idx_user_activity (user_id, created_at DESC),
    INDEX idx_activity_type (activity_type, created_at DESC),
    INDEX idx_points (points DESC),
    INDEX idx_related_entity (related_entity_type, related_entity_id)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

--User Interactions - Detailed interaction logging
CREATE TABLE IF NOT EXISTS user_interactions (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,    
    user_id VARCHAR(36) NOT NULL,
    interaction_type ENUM('review_processing_complete','review_analysis_complete','view_feedback_tab','view_code_generator','analysis_complete','review_analysis_start','start_review','code_ready_for_review','generate_completed','start_generate','view_badge_showcase','deselect_category','select_category','submit_review','complete_tutorial_abandoned','code_generate_complete','start_tutorial_code_generation','filter_by_difficulty','filter_by_category','regenerate_tutorial_code') NOT NULL,
    interaction_category VARCHAR(50) NOT NULL,   
    details JSON,
    time_spent_seconds INT DEFAULT 0,
    success BOOLEAN DEFAULT TRUE,      
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,    
   
    FOREIGN KEY (user_id) REFERENCES users(uid) ON DELETE CASCADE,
    INDEX idx_user_timestamp (user_id, timestamp DESC),
    INDEX idx_interaction_type (interaction_type, timestamp DESC)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;


CREATE VIEW user_practice_summary AS
SELECT 
    u.uid as user_id,
    u.display_name_en,
    u.display_name_zh,
    COUNT(uep.id) as total_errors_practiced,
    SUM(CASE WHEN uep.completion_status = 'completed' THEN 1 ELSE 0 END) as completed_errors,
    SUM(CASE WHEN uep.completion_status = 'mastered' THEN 1 ELSE 0 END) as mastered_errors,
    AVG(uep.best_accuracy) as average_accuracy,
    SUM(uep.total_time_spent) as total_practice_time,
    MAX(uep.last_practiced) as last_practice_session
FROM users u
LEFT JOIN user_error_practice uep ON u.uid = uep.user_id
GROUP BY u.uid, u.display_name_en, u.display_name_zh;

-- Verification and status
SELECT 'Database tables created successfully!' as Status;
SELECT COUNT(table_name) as Tables_Created 
FROM information_schema.tables 
WHERE table_schema = DATABASE() 
AND table_name IN ('users', 'error_categories', 'java_errors', 'badges', 'user_badges', 'activity_log','user_interactions','error_category_stats', 'review_sessions', 'badge_progress', 'user_streaks');   

