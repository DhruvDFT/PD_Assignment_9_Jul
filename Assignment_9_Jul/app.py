# Enhanced PD Assessment System - Complete app.py for Railway
import os
import hashlib
import json
import random
import sqlite3
from datetime import datetime, timedelta
from threading import Lock
from flask import Flask, request, redirect, session, jsonify, render_template_string
import re

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'pd-secret-key-enhanced')

# Database setup
DATABASE = 'enhanced_assessments.db'
db_lock = Lock()

class DatabaseManager:
    @staticmethod
    def init_db():
        """Initialize SQLite database with enhanced schema"""
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        
        # Users table
        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE,
                display_name TEXT,
                email TEXT,
                password TEXT,
                is_admin BOOLEAN DEFAULT 0,
                experience INTEGER DEFAULT 3,
                department TEXT,
                created_date TEXT,
                last_login TEXT,
                theme TEXT DEFAULT 'light'
            )
        """)
        
        # Assignments table
        c.execute("""
            CREATE TABLE IF NOT EXISTS assignments (
                id TEXT PRIMARY KEY,
                engineer_id TEXT,
                topic TEXT,
                questions TEXT,
                created_date TEXT,
                due_date TEXT,
                status TEXT DEFAULT 'pending',
                difficulty_level INTEGER DEFAULT 1,
                max_points INTEGER DEFAULT 180,
                created_by TEXT,
                FOREIGN KEY (engineer_id) REFERENCES users (id)
            )
        """)
        
        # Submissions table (enhanced)
        c.execute("""
            CREATE TABLE IF NOT EXISTS submissions (
                id TEXT PRIMARY KEY,
                assignment_id TEXT,
                engineer_id TEXT,
                answers TEXT,
                submitted_date TEXT,
                status TEXT DEFAULT 'submitted',
                auto_scores TEXT,
                manual_scores TEXT,
                feedback TEXT,
                total_score INTEGER DEFAULT 0,
                graded_by TEXT,
                graded_date TEXT,
                time_spent INTEGER DEFAULT 0,
                FOREIGN KEY (assignment_id) REFERENCES assignments (id),
                FOREIGN KEY (engineer_id) REFERENCES users (id)
            )
        """)
        
        # Analytics table
        c.execute("""
            CREATE TABLE IF NOT EXISTS analytics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT,
                user_id TEXT,
                data TEXT,
                timestamp TEXT
            )
        """)
        
        conn.commit()
        conn.close()
    
    @staticmethod
    def log_analytics(event_type, user_id, data=None):
        """Log analytics events"""
        with db_lock:
            conn = sqlite3.connect(DATABASE)
            c = conn.cursor()
            c.execute("""
                INSERT INTO analytics (event_type, user_id, data, timestamp)
                VALUES (?, ?, ?, ?)
            """, (event_type, user_id, json.dumps(data) if data else None, datetime.now().isoformat()))
            conn.commit()
            conn.close()

# Enhanced Question Generation with Smart AI
class SmartQuestionGenerator:
    def __init__(self):
        self.question_templates = {
            "sta": [
                {
                    "template": "Your design has {violation_type} violations of {violation_amount}ps on {num_paths} critical paths. The design is running at {frequency}MHz. Analyze the root causes and propose {num_solutions} specific solutions with expected improvement estimates.",
                    "difficulty": 3,
                    "parameters": {
                        "violation_type": ["setup", "hold", "max_transition"],
                        "violation_amount": [20, 50, 100, 150, 200],
                        "num_paths": [10, 25, 50, 100, 200],
                        "frequency": [500, 800, 1000, 1500, 2000],
                        "num_solutions": [3, 4, 5]
                    }
                },
                {
                    "template": "Explain the concept of {concept} in static timing analysis. How does it impact {impact_area} and what are the industry-standard approaches to handle it in {technology_node} designs?",
                    "difficulty": 2,
                    "parameters": {
                        "concept": ["clock jitter", "OCV", "useful skew", "clock latency", "timing corners"],
                        "impact_area": ["setup timing", "hold timing", "power consumption", "area optimization"],
                        "technology_node": ["7nm", "5nm", "3nm", "advanced nodes"]
                    }
                },
                {
                    "template": "You're analyzing a {design_type} with {num_domains} clock domains running at different frequencies. Describe your approach to handle clock domain crossings and ensure timing closure across all interfaces.",
                    "difficulty": 4,
                    "parameters": {
                        "design_type": ["SoC", "CPU", "GPU", "AI accelerator"],
                        "num_domains": [3, 4, 5, 6]
                    }
                }
            ],
            "cts": [
                {
                    "template": "Design a clock tree for a {design_size} design with {num_flops} flip-flops distributed across {die_size}. The target skew is {target_skew}ps and you have {buffer_types} buffer types available. Explain your tree topology choice and optimization strategy.",
                    "difficulty": 3,
                    "parameters": {
                        "design_size": ["large-scale", "medium-scale", "complex"],
                        "num_flops": [10000, 25000, 50000, 100000],
                        "die_size": ["5mm x 5mm", "10mm x 10mm", "15mm x 15mm"],
                        "target_skew": [25, 50, 75, 100],
                        "buffer_types": [3, 4, 5, 6]
                    }
                },
                {
                    "template": "Your clock tree has {power_consumption}mW power consumption, which is {percentage}% of total chip power. Propose {num_techniques} specific techniques to reduce clock power while maintaining {skew_constraint}ps skew constraint.",
                    "difficulty": 4,
                    "parameters": {
                        "power_consumption": [50, 100, 150, 200],
                        "percentage": [15, 20, 25, 30, 35],
                        "num_techniques": [3, 4, 5],
                        "skew_constraint": [30, 50, 75]
                    }
                }
            ],
            "signoff": [
                {
                    "template": "Your design failed {check_type} with {num_violations} violations. The violations are distributed as: {violation_dist}. Create a systematic debugging and resolution plan with priority ordering and estimated effort.",
                    "difficulty": 3,
                    "parameters": {
                        "check_type": ["DRC", "LVS", "Antenna", "Metal Density"],
                        "num_violations": [50, 100, 200, 500],
                        "violation_dist": ["70% spacing, 20% width, 10% via", "50% density, 30% spacing, 20% antenna"]
                    }
                },
                {
                    "template": "Perform signoff analysis for a {design_type} in {technology} process. The design has {power_domains} power domains and {io_count} I/Os. List all required signoff checks and create a verification plan with timeline.",
                    "difficulty": 4,
                    "parameters": {
                        "design_type": ["automotive SoC", "mobile processor", "IoT chip", "high-performance CPU"],
                        "technology": ["7nm FinFET", "5nm", "3nm GAA"],
                        "power_domains": [2, 3, 4, 5],
                        "io_count": [100, 200, 500, 1000]
                    }
                }
            ]
        }
    
    def generate_smart_questions(self, topic, num_questions=18, engineer_exp=3):
        """Generate questions with adaptive difficulty"""
        templates = self.question_templates.get(topic, [])
        if not templates:
            return self._fallback_questions(topic)
        
        questions = []
        difficulty_distribution = self._get_difficulty_distribution(engineer_exp, num_questions)
        
        for target_difficulty in difficulty_distribution:
            suitable_templates = [t for t in templates if abs(t["difficulty"] - target_difficulty) <= 1]
            if not suitable_templates:
                suitable_templates = templates
            
            template = random.choice(suitable_templates)
            question = self._generate_from_template(template)
            questions.append(question)
        
        return questions[:num_questions]
    
    def _get_difficulty_distribution(self, engineer_exp, num_questions):
        """Create difficulty distribution based on experience"""
        if engineer_exp <= 2:
            easy_count = int(num_questions * 0.6)
            medium_count = int(num_questions * 0.3)
            hard_count = num_questions - easy_count - medium_count
            return [2] * easy_count + [3] * medium_count + [4] * hard_count
        elif engineer_exp <= 4:
            easy_count = int(num_questions * 0.3)
            medium_count = int(num_questions * 0.5)
            hard_count = num_questions - easy_count - medium_count
            return [2] * easy_count + [3] * medium_count + [4] * hard_count
        else:
            easy_count = int(num_questions * 0.2)
            medium_count = int(num_questions * 0.4)
            hard_count = num_questions - easy_count - medium_count
            return [2] * easy_count + [3] * medium_count + [4] * hard_count
    
    def _generate_from_template(self, template_data):
        """Generate question from template with random parameters"""
        template = template_data["template"]
        params = template_data["parameters"]
        
        generated_params = {}
        for param, options in params.items():
            generated_params[param] = random.choice(options)
        
        try:
            return template.format(**generated_params)
        except KeyError:
            return template
    
    def _fallback_questions(self, topic):
        """Fallback to static questions if smart generation fails"""
        fallback = {
            "sta": [
                "What is Static Timing Analysis and why is it critical in modern chip design?",
                "Explain setup and hold time violations. How do you debug and fix them?",
                "What is clock skew and how does it impact timing closure?",
                "Describe the concept of timing corners and their importance in analysis.",
                "How do you handle timing analysis for multiple clock domains?",
                "What are timing exceptions and when would you use false paths?",
                "Explain the difference between ideal clock and propagated clock analysis.",
                "What is clock jitter and how do you account for it in timing calculations?",
                "How do you analyze timing for memory interfaces and what makes them special?",
                "What is OCV (On-Chip Variation) and why do you add OCV margins in STA?",
                "Explain multicycle paths and give an example where you would use them.",
                "How do you handle timing analysis for generated clocks and clock dividers?",
                "What is clock domain crossing (CDC) and what timing checks are needed?",
                "Describe timing analysis for high-speed interfaces and their challenges.",
                "What reports do you check for timing signoff and why are they important?",
                "How do you ensure timing correlation between STA tools and silicon?",
                "What is useful skew and how can it help with timing closure?",
                "Explain timing optimization techniques for low-power designs."
            ],
            "cts": [
                "What is Clock Tree Synthesis and what are its main objectives?",
                "Explain different clock tree topologies and when to use each.",
                "How do you optimize clock trees for power consumption?",
                "What is useful skew and how can it help timing closure?",
                "Describe challenges in CTS for high-frequency designs.",
                "What is clock skew and what causes it in clock trees?",
                "How do you handle clock gating cells in clock tree synthesis?",
                "Explain the concept of clock insertion delay and how to minimize it.",
                "What are the trade-offs between H-tree and balanced tree topologies?",
                "How do you handle multiple clock domains in CTS?",
                "What is clock mesh and when would you choose it over tree topology?",
                "Describe clock tree optimization for process variation and yield.",
                "How do you build clock trees for multi-voltage designs?",
                "What is the typical CTS flow and when does it happen in the design cycle?",
                "How do you verify clock tree quality after synthesis?",
                "What are the challenges of clock tree synthesis in advanced nodes?",
                "Explain clock tree balancing and why it's important.",
                "How do you handle clock tree synthesis for low-power designs?"
            ],
            "signoff": [
                "What are the main signoff checks required before tape-out?",
                "Explain DRC violations and systematic approaches to fix them.",
                "What is LVS and how do you debug LVS mismatches?",
                "Describe IR drop analysis and mitigation techniques.",
                "How do you perform timing signoff for multi-corner analysis?",
                "What is antenna checking and why can violations damage your chip?",
                "Explain metal density rules and their impact on manufacturing.",
                "What is electromigration and how do you prevent EM violations?",
                "How do you perform signal integrity analysis during signoff?",
                "What is formal verification and how does it differ from simulation?",
                "Describe the signoff flow for advanced technology nodes.",
                "How do you coordinate signoff across different design teams?",
                "What additional checks are needed for multi-voltage designs?",
                "Explain thermal analysis and its importance in signoff.",
                "What is yield analysis and how do you optimize for manufacturing yield?",
                "How do you validate power delivery networks during signoff?",
                "What are the challenges of signoff in 7nm and below technologies?",
                "Describe the handoff process between design and manufacturing teams."
            ]
        }
        
        base_questions = fallback.get(topic, fallback["sta"])
        extended = []
        for i in range(18):
            base_q = base_questions[i % len(base_questions)]
            if i >= len(base_questions):
                extended.append(f"Advanced: {base_q}")
            else:
                extended.append(base_q)
        return extended

# Enhanced Scoring System
class EnhancedScoringSystem:
    def __init__(self):
        self.scoring_rubrics = {
            "sta": {
                "technical_terms": ["setup", "hold", "slack", "skew", "jitter", "corner", "violation", "closure"],
                "advanced_terms": ["ocv", "cppr", "useful skew", "clock latency", "propagated", "ideal"],
                "methodology_terms": ["debug", "optimize", "analyze", "systematic", "root cause"],
                "weights": {"technical": 0.4, "depth": 0.3, "methodology": 0.2, "clarity": 0.1}
            },
            "cts": {
                "technical_terms": ["clock tree", "skew", "insertion delay", "buffer", "topology", "synthesis"],
                "advanced_terms": ["h-tree", "mesh", "useful skew", "gating", "power optimization"],
                "methodology_terms": ["balance", "optimize", "strategy", "approach", "technique"],
                "weights": {"technical": 0.4, "depth": 0.3, "methodology": 0.2, "clarity": 0.1}
            },
            "signoff": {
                "technical_terms": ["drc", "lvs", "antenna", "density", "ir drop", "em", "signoff"],
                "advanced_terms": ["formal verification", "multi-corner", "yield analysis", "si analysis"],
                "methodology_terms": ["debug", "systematic", "flow", "process", "validation"],
                "weights": {"technical": 0.4, "depth": 0.3, "methodology": 0.2, "clarity": 0.1}
            }
        }
    
    def analyze_answer_comprehensive(self, question, answer, topic):
        """Comprehensive answer analysis with detailed feedback"""
        if not answer or len(answer.strip()) < 20:
            return {
                "score": 0,
                "breakdown": {"technical": 0, "depth": 0, "methodology": 0, "clarity": 0},
                "feedback": "Answer too short or empty",
                "suggestions": ["Provide more detailed technical explanation", "Include specific examples", "Explain methodology"]
            }
        
        rubric = self.scoring_rubrics.get(topic, self.scoring_rubrics["sta"])
        answer_lower = answer.lower()
        word_count = len(answer.split())
        
        # Technical accuracy score
        technical_score = self._score_technical_content(answer_lower, rubric)
        
        # Depth and detail score
        depth_score = self._score_depth(answer, word_count)
        
        # Methodology score
        methodology_score = self._score_methodology(answer_lower, rubric)
        
        # Clarity and structure score
        clarity_score = self._score_clarity(answer)
        
        # Weighted final score
        weights = rubric["weights"]
        final_score = (
            technical_score * weights["technical"] +
            depth_score * weights["depth"] +
            methodology_score * weights["methodology"] +
            clarity_score * weights["clarity"]
        ) * 10
        
        # Generate feedback and suggestions
        feedback, suggestions = self._generate_feedback(
            technical_score, depth_score, methodology_score, clarity_score, word_count
        )
        
        return {
            "score": round(final_score, 1),
            "breakdown": {
                "technical": round(technical_score * 10, 1),
                "depth": round(depth_score * 10, 1),
                "methodology": round(methodology_score * 10, 1),
                "clarity": round(clarity_score * 10, 1)
            },
            "feedback": feedback,
            "suggestions": suggestions,
            "word_count": word_count
        }
    
    def _score_technical_content(self, answer_lower, rubric):
        tech_terms = sum(1 for term in rubric["technical_terms"] if term in answer_lower)
        advanced_terms = sum(1 for term in rubric["advanced_terms"] if term in answer_lower)
        
        tech_score = min(tech_terms / 3, 1.0)
        advanced_score = min(advanced_terms / 2, 0.5)
        
        return min(tech_score + advanced_score, 1.0)
    
    def _score_depth(self, answer, word_count):
        word_score = min(word_count / 100, 0.7)
        
        has_examples = any(marker in answer.lower() for marker in ['example', 'for instance', 'such as'])
        has_numbers = bool(re.search(r'\d+', answer))
        has_comparisons = any(marker in answer.lower() for marker in ['compare', 'versus', 'vs', 'better', 'worse'])
        
        structure_score = (has_examples * 0.1) + (has_numbers * 0.1) + (has_comparisons * 0.1)
        
        return min(word_score + structure_score, 1.0)
    
    def _score_methodology(self, answer_lower, rubric):
        method_terms = sum(1 for term in rubric["methodology_terms"] if term in answer_lower)
        
        has_steps = any(marker in answer_lower for marker in ['step', 'first', 'second', 'then', 'next', 'finally'])
        has_process = any(marker in answer_lower for marker in ['process', 'flow', 'procedure', 'approach'])
        
        method_score = min(method_terms / 2, 0.7)
        process_score = (has_steps * 0.15) + (has_process * 0.15)
        
        return min(method_score + process_score, 1.0)
    
    def _score_clarity(self, answer):
        sentences = answer.split('.')
        avg_sentence_length = sum(len(s.split()) for s in sentences) / max(len(sentences), 1)
        
        length_score = 1.0 - abs(avg_sentence_length - 17.5) / 17.5
        length_score = max(0, min(length_score, 1.0))
        
        has_organization = any(marker in answer.lower() for marker in [':', '-', '1.', '2.', 'bullet'])
        org_score = 0.3 if has_organization else 0
        
        return min(length_score * 0.7 + org_score, 1.0)
    
    def _generate_feedback(self, tech_score, depth_score, method_score, clarity_score, word_count):
        feedback_parts = []
        suggestions = []
        
        if tech_score >= 0.8:
            feedback_parts.append("Strong technical knowledge demonstrated")
        elif tech_score >= 0.6:
            feedback_parts.append("Good technical understanding shown")
            suggestions.append("Include more specific technical terminology")
        else:
            feedback_parts.append("Limited technical content")
            suggestions.append("Use more industry-specific technical terms")
        
        if depth_score >= 0.8:
            feedback_parts.append("comprehensive analysis provided")
        elif depth_score >= 0.6:
            feedback_parts.append("adequate detail level")
            suggestions.append("Provide more detailed explanations and examples")
        else:
            feedback_parts.append("needs more depth")
            suggestions.append("Expand with specific examples and quantitative details")
        
        if method_score >= 0.7:
            feedback_parts.append("clear methodology described")
        else:
            feedback_parts.append("methodology could be clearer")
            suggestions.append("Describe step-by-step approach or process")
        
        if word_count < 50:
            suggestions.append("Increase answer length for better coverage")
        elif word_count > 300:
            suggestions.append("Consider more concise explanations")
        
        feedback = ", ".join(feedback_parts).capitalize() + f" ({word_count} words)"
        
        return feedback, suggestions

# Initialize components
DatabaseManager.init_db()
question_generator = SmartQuestionGenerator()
scoring_system = EnhancedScoringSystem()

# User authentication functions
def hash_pass(pwd):
    return hashlib.sha256(pwd.encode()).hexdigest()

def check_pass(hashed, pwd):
    return hashed == hashlib.sha256(pwd.encode()).hexdigest()

def init_data():
    """Initialize demo data"""
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    # Check if admin exists
    c.execute('SELECT id FROM users WHERE id = ?', ('admin',))
    if not c.fetchone():
        # Create admin
        c.execute("""
            INSERT INTO users (id, username, display_name, email, password, is_admin, experience, created_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, ('admin', 'admin', 'System Administrator', 'admin@vibhuayu.com', 
              hash_pass('Vibhuaya@3006'), 1, 5, datetime.now().isoformat()))
        
        # Create 18 engineers
        engineer_data = [
            ('eng001', 'Kranthi', 'kranthi@vibhuayu.com', 3),
            ('eng002', 'Neela', 'neela@vibhuayu.com', 4),
            ('eng003', 'Bhanu', 'bhanu@vibhuayu.com', 2),
            ('eng004', 'Lokeshwari', 'lokeshwari@vibhuayu.com', 5),
            ('eng005', 'Nagesh', 'nagesh@vibhuayu.com', 3),
            ('eng006', 'VJ', 'vj@vibhuayu.com', 4),
            ('eng007', 'Pravalika', 'pravalika@vibhuayu.com', 2),
            ('eng008', 'Daniel', 'daniel@vibhuayu.com', 6),
            ('eng009', 'Karthik', 'karthik@vibhuayu.com', 3),
            ('eng010', 'Hema', 'hema@vibhuayu.com', 4),
            ('eng011', 'Naveen', 'naveen@vibhuayu.com', 5),
            ('eng012', 'Srinivas', 'srinivas@vibhuayu.com', 3),
            ('eng013', 'Meera', 'meera@vibhuayu.com', 2),
            ('eng014', 'Suraj', 'suraj@vibhuayu.com', 4),
            ('eng015', 'Akhil', 'akhil@vibhuayu.com', 3),
            ('eng016', 'Vikas', 'vikas@vibhuayu.com', 5),
            ('eng017', 'Sahith', 'sahith@vibhuayu.com', 2),
            ('eng018', 'Sravan', 'sravan@vibhuayu.com', 4)
        ]
        
        for uid, name, email, exp in engineer_data:
            c.execute("""
                INSERT INTO users (id, username, display_name, email, password, is_admin, experience, department, created_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (uid, uid, name, email, hash_pass('password123'), 0, exp, 'Physical Design', datetime.now().isoformat()))
    
    conn.commit()
    conn.close()

def _time_ago(date_str):
    """Calculate time ago from date string"""
    try:
        date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        now = datetime.now()
        diff = now - date_obj
        
        if diff.days > 0:
            return f"{diff.days}d ago"
        elif diff.seconds > 3600:
            return f"{diff.seconds // 3600}h ago"
        elif diff.seconds > 60:
            return f"{diff.seconds // 60}m ago"
        else:
            return "Just now"
    except:
        return "Unknown"

# Routes
@app.route('/')
def home():
    if 'user_id' in session:
        if session.get('is_admin'):
            return redirect('/admin')
        return redirect('/student')
    return redirect('/login')

@app.route('/health')
def health():
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE username = ?', (username,))
        user = c.fetchone()
        conn.close()
        
        if user and check_pass(user[4], password):
            session['user_id'] = user[0]
            session['username'] = user[1]
            session['display_name'] = user[2]
            session['is_admin'] = bool(user[5])
            session['theme'] = user[10] if user[10] else 'light'
            
            # Update last login
            conn = sqlite3.connect(DATABASE)
            c = conn.cursor()
            c.execute('UPDATE users SET last_login = ? WHERE id = ?', 
                     (datetime.now().isoformat(), user[0]))
            conn.commit()
            conn.close()
            
            # Log analytics
            DatabaseManager.log_analytics('login', user[0])
            
            if bool(user[5]):
                return redirect('/admin')
            return redirect('/student')
    
    # Enhanced login page
    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
    <title>Vibhuayu Technologies - Enhanced PD Assessment</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        :root {
            --primary-color: #667eea;
            --secondary-color: #764ba2;
            --success-color: #10b981;
            --warning-color: #f59e0b;
            --error-color: #ef4444;
            --bg-primary: #0f172a;
            --bg-secondary: #1e293b;
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --surface: rgba(255, 255, 255, 0.98);
            --border: #e2e8f0;
        }
        
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            background: linear-gradient(135deg, var(--bg-primary) 0%, var(--bg-secondary) 100%); 
            min-height: 100vh; 
            display: flex; 
            align-items: center; 
            justify-content: center; 
            position: relative;
            overflow-x: hidden;
        }
        
        body::before {
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0; bottom: 0;
            background: 
                radial-gradient(circle at 30% 40%, rgba(102, 126, 234, 0.3) 0%, transparent 50%),
                radial-gradient(circle at 80% 80%, rgba(118, 75, 162, 0.15) 0%, transparent 50%);
            z-index: 1;
        }
        
        .container {
            position: relative; z-index: 2;
            background: var(--surface);
            backdrop-filter: blur(20px);
            border-radius: 24px;
            padding: 50px 40px;
            width: min(450px, 90vw);
            box-shadow: 0 25px 50px rgba(0, 0, 0, 0.25);
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        .logo-section {
            text-align: center;
            margin-bottom: 35px;
        }
        
        .logo {
            width: 80px; height: 80px;
            margin: 0 auto 20px;
            background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
            border-radius: 20px;
            display: flex; align-items: center; justify-content: center;
            color: white; font-size: 36px; font-weight: 900;
            box-shadow: 0 10px 30px rgba(102, 126, 234, 0.3);
            position: relative; overflow: hidden;
        }
.logo::before {
            content: ''; position: absolute;
            top: 0; left: 0; right: 0; bottom: 0;
            background: linear-gradient(45deg, transparent 30%, rgba(255,255,255,0.1) 50%, transparent 70%);
            transform: translateX(-100%);
            animation: shine 3s infinite;
        }
        
        @keyframes shine {
            0% { transform: translateX(-100%); }
            50% { transform: translateX(100%); }
            100% { transform: translateX(100%); }
        }
        
        .title {
            font-size: 28px; font-weight: 700;
            background: linear-gradient(135deg, #1e293b, #475569);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            margin-bottom: 8px;
        }
        
        .subtitle {
            color: #64748b; font-size: 16px; font-weight: 500;
            margin-bottom: 35px;
        }
        
        .form-group {
            margin-bottom: 24px;
        }
        
        .form-group label {
            display: block; margin-bottom: 8px;
            color: #374151; font-weight: 600; font-size: 14px;
        }
        
        .form-input {
            width: 100%; padding: 16px 20px;
            border: 2px solid var(--border);
            border-radius: 12px; font-size: 16px;
            transition: all 0.3s ease;
            background: rgba(255, 255, 255, 0.8);
        }
        
        .form-input:focus {
            outline: none; border-color: var(--primary-color);
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
            background: white;
        }
        
        .login-btn {
            width: 100%; padding: 16px;
            background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
            color: white; border: none; border-radius: 12px;
            font-size: 16px; font-weight: 600; cursor: pointer;
            transition: all 0.3s ease; margin-bottom: 30px;
        }
        
        .login-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 25px rgba(102, 126, 234, 0.4);
        }
        
        .info-card {
            background: linear-gradient(135deg, #f8fafc, #f1f5f9);
            border: 1px solid var(--border);
            border-radius: 16px; padding: 24px; text-align: center;
        }
        
        .credentials {
            background: white; border-radius: 8px; padding: 12px;
            margin: 12px 0; border-left: 4px solid var(--primary-color);
        }
        
        .feature-highlights {
            margin-top: 15px; font-size: 12px; color: #64748b;
            line-height: 1.6;
        }
        
        .new-badge {
            background: var(--success-color); color: white;
            padding: 2px 6px; border-radius: 10px;
            font-size: 10px; font-weight: 600; margin-left: 5px;
        }
        
        @media (max-width: 480px) {
            .container { padding: 30px 20px; }
            .title { font-size: 24px; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="logo-section">
            <div class="logo">V7</div>
            <div class="title">Enhanced PD Portal</div>
            <div class="subtitle">Advanced Assessment & Analytics System</div>
        </div>
        
        <form method="POST">
            <div class="form-group">
                <label>Username</label>
                <input type="text" name="username" class="form-input" 
                       placeholder="Enter your username" required autocomplete="username">
            </div>
            <div class="form-group">
                <label>Password</label>
                <input type="password" name="password" class="form-input" 
                       placeholder="Enter your password" required autocomplete="current-password">
            </div>
            <button type="submit" class="login-btn">Access Enhanced Portal</button>
        </form>
        
        <div class="info-card">
            <div style="font-weight: 700; margin-bottom: 16px;">🔐 Demo Credentials</div>
            <div class="credentials">
                <strong>Engineers:</strong> eng001 through eng018<br>
                <strong>Password:</strong> password123<br>
                <strong>Admin:</strong> admin / Vibhuaya@3006
            </div>
            <div class="feature-highlights">
                <strong>🚀 New Features:</strong><br>
                Smart Question Generation <span class="new-badge">NEW</span><br>
                Enhanced AI Scoring <span class="new-badge">NEW</span><br>
                Performance Analytics <span class="new-badge">NEW</span><br>
                Mobile-Responsive Design <span class="new-badge">NEW</span>
            </div>
        </div>
    </div>
</body>
</html>""")

@app.route('/logout')
def logout():
    user_id = session.get('user_id')
    if user_id:
        DatabaseManager.log_analytics('logout', user_id)
    
    session.clear()
    return redirect('/login')

@app.route('/admin')
def admin():
    if not session.get('is_admin'):
        return redirect('/login')
    
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    # Get comprehensive statistics
    c.execute('SELECT COUNT(*) FROM users WHERE is_admin = 0')
    total_engineers = c.fetchone()[0]
    
    c.execute('SELECT COUNT(*) FROM assignments')
    total_assignments = c.fetchone()[0]
    
    c.execute('SELECT COUNT(*) FROM submissions WHERE status = "submitted"')
    pending_reviews = c.fetchone()[0]
    
    c.execute('SELECT COUNT(*) FROM submissions WHERE status = "graded"')
    completed_reviews = c.fetchone()[0]
    
    # Get engineers for dropdown
    c.execute('SELECT * FROM users WHERE is_admin = 0 ORDER BY display_name')
    engineers = c.fetchall()
    
    # Get recent activity
    c.execute('''
        SELECT s.*, a.topic, u.display_name, a.created_date as assignment_date
        FROM submissions s
        JOIN assignments a ON s.assignment_id = a.id
        JOIN users u ON s.engineer_id = u.id
        WHERE s.status = "submitted"
        ORDER BY s.submitted_date DESC
        LIMIT 10
    ''')
    pending_submissions = c.fetchall()
    
    # Get performance analytics
    c.execute('''
        SELECT 
            topic,
            COUNT(*) as count,
            AVG(CAST(total_score as FLOAT)) as avg_score,
            MAX(CAST(total_score as FLOAT)) as max_score,
            MIN(CAST(total_score as FLOAT)) as min_score
        FROM submissions s
        JOIN assignments a ON s.assignment_id = a.id
        WHERE s.status = "graded" AND s.total_score > 0
        GROUP BY topic
    ''')
    topic_stats = c.fetchall()
    
    conn.close()
    
    # Build engineer options
    eng_options = ''
    for eng in engineers:
        exp_years = eng[6] if eng[6] else 3
        eng_options += f'<option value="{eng[0]}" data-exp="{exp_years}">{eng[2]} ({exp_years}y exp)</option>'
    
    # Build pending submissions HTML
    pending_html = ''
    for sub in pending_submissions:
        time_ago = _time_ago(sub[4])
        pending_html += f'''
        <div class="submission-card">
            <div class="submission-header">
                <h4>{sub[11]} - {sub[10].upper()}</h4>
                <span class="time-badge">{time_ago}</span>
            </div>
            <div class="submission-meta">
                📝 {len(json.loads(sub[3]))} answers | 🎯 Auto-scored | ⏰ {sub[4][:16]}
            </div>
            <div class="submission-actions">
                <a href="/admin/review/{sub[1]}" class="review-btn">Review & Grade</a>
            </div>
        </div>'''
    
    if not pending_html:
        pending_html = '''
        <div class="no-submissions">
            <div class="empty-icon">📭</div>
            <h3>All Caught Up!</h3>
            <p>No pending submissions to review. Great work!</p>
        </div>'''
    
    # Build analytics charts data
    analytics_data = {
        "topic_stats": [{"topic": stat[0], "count": stat[1], "avg_score": round(stat[2], 1)} for stat in topic_stats],
        "total_engineers": total_engineers,
        "completion_rate": round((completed_reviews / max(total_assignments, 1)) * 100, 1)
    }
    
    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
    <title>Enhanced Admin Dashboard - Vibhuayu</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        :root {
            --primary: #667eea;
            --secondary: #764ba2;
            --success: #10b981;
            --warning: #f59e0b;
            --error: #ef4444;
            --bg-dark: #0f172a;
            --bg-light: #1e293b;
            --surface: #ffffff;
            --text-primary: #1e293b;
            --text-secondary: #64748b;
            --border: #e2e8f0;
        }
        
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, var(--bg-dark) 0%, var(--bg-light) 100%);
            min-height: 100vh; color: var(--text-primary);
        }
        
        .header {
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            padding: 20px 0; box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
            position: relative; overflow: hidden;
        }
        
        .header::before {
            content: ''; position: absolute;
            top: 0; left: 0; right: 0; bottom: 0;
            background: linear-gradient(45deg, transparent 30%, rgba(255,255,255,0.1) 50%, transparent 70%);
            transform: translateX(-100%);
            animation: headerShine 4s infinite;
        }
        
        @keyframes headerShine {
            0% { transform: translateX(-100%); }
            50% { transform: translateX(100%); }
            100% { transform: translateX(100%); }
        }
        
        .header-content {
            max-width: 1400px; margin: 0 auto; padding: 0 20px;
            display: flex; align-items: center; justify-content: space-between;
            position: relative; z-index: 2;
        }
        
        .header-title {
            display: flex; align-items: center; gap: 15px;
        }
        
        .header-logo {
            width: 50px; height: 50px;
            background: rgba(255, 255, 255, 0.15);
            border-radius: 12px; display: flex; align-items: center; justify-content: center;
            font-weight: 900; color: white; font-size: 20px;
            backdrop-filter: blur(10px);
        }
        
        .header h1 {
            color: white; font-size: 28px; font-weight: 700;
            text-shadow: 0 2px 10px rgba(0,0,0,0.3);
        }
        
        .nav-menu {
            display: flex; gap: 15px; align-items: center;
        }
        
        .nav-btn {
            background: rgba(255, 255, 255, 0.15); color: white;
            padding: 10px 15px; text-decoration: none; border-radius: 8px;
            backdrop-filter: blur(10px); transition: all 0.3s ease;
            font-weight: 600; font-size: 14px;
        }
        
        .nav-btn:hover {
            background: rgba(255, 255, 255, 0.25);
            transform: translateY(-2px);
        }
        
        .container {
            max-width: 1400px; margin: 30px auto; padding: 0 20px;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 25px; margin-bottom: 40px;
        }
        
        .stat-card {
            background: linear-gradient(135deg, var(--surface) 0%, #f8fafc 100%);
            padding: 30px; border-radius: 20px; text-align: center;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.2);
            transition: transform 0.3s ease;
        }
        
        .stat-card:hover { transform: translateY(-5px); }
        
        .stat-number {
            font-size: 42px; font-weight: 800;
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            margin-bottom: 8px; line-height: 1;
        }
        
        .stat-label {
            color: var(--text-secondary); font-weight: 600;
            font-size: 14px; text-transform: uppercase; letter-spacing: 1px;
        }
        
        .stat-trend {
            margin-top: 10px; font-size: 12px; font-weight: 600;
        }
        
        .trend-up { color: var(--success); }
        .trend-down { color: var(--error); }
        
        .main-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
        }
        
        .card {
            background: linear-gradient(135deg, var(--surface) 0%, #f8fafc 100%);
            border-radius: 20px; padding: 30px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.2);
        }
        
        .card h2 {
            color: var(--text-primary); margin-bottom: 25px;
            font-size: 24px; font-weight: 700;
            display: flex; align-items: center; gap: 10px;
        }
        
        .form-row {
            display: grid;
            grid-template-columns: 1fr 1fr auto;
            gap: 15px; align-items: end;
        }
        
        .form-group {
            display: flex; flex-direction: column;
        }
        
        .form-group label {
            margin-bottom: 8px; font-weight: 600;
            color: var(--text-primary); font-size: 14px;
        }
        
        select, button {
            padding: 14px 18px; border: 2px solid var(--border);
            border-radius: 12px; font-size: 16px;
            transition: all 0.3s ease; background: white;
            font-family: inherit;
        }
        
        select:focus {
            outline: none; border-color: var(--primary);
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }
        
        .btn-primary {
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            color: white; border: none; cursor: pointer;
            font-weight: 600; min-width: 140px;
        }
        
        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 25px rgba(102, 126, 234, 0.4);
        }
        
        .submission-card {
            background: linear-gradient(135deg, #f8fafc, #f1f5f9);
            padding: 20px; margin: 15px 0; border-radius: 16px;
            border-left: 4px solid var(--warning);
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.05);
            transition: all 0.3s ease;
        }
        
        .submission-card:hover {
            transform: translateX(5px);
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);
        }
        
        .submission-header {
            display: flex; justify-content: space-between;
            align-items: center; margin-bottom: 10px;
        }
        
        .submission-header h4 {
            color: var(--text-primary); margin: 0; font-size: 16px;
        }
        
        .time-badge {
            background: var(--warning); color: white;
            padding: 4px 12px; border-radius: 20px;
            font-size: 12px; font-weight: 600;
        }
        
        .submission-meta {
            color: var(--text-secondary); font-size: 14px;
            margin-bottom: 15px;
        }
        
        .submission-actions {
            display: flex; gap: 10px;
        }
        
        .review-btn {
            padding: 8px 16px; text-decoration: none;
            border-radius: 8px; font-weight: 600;
            font-size: 14px; transition: all 0.3s ease;
            background: linear-gradient(135deg, var(--success), #059669);
            color: white;
        }
        
        .review-btn:hover {
            transform: translateY(-2px);
        }
        
        .no-submissions {
            text-align: center; padding: 60px 20px;
            color: var(--text-secondary);
        }
        
        .empty-icon {
            font-size: 48px; margin-bottom: 20px;
        }
        
        .analytics-preview {
            background: linear-gradient(135deg, #f0f9ff, #e0f2fe);
            border-radius: 12px; padding: 20px;
            margin-top: 20px;
        }
        
        .analytics-item {
            display: flex; justify-content: space-between;
            align-items: center; padding: 10px 0;
            border-bottom: 1px solid rgba(102, 126, 234, 0.1);
        }
        
        .analytics-item:last-child { border-bottom: none; }
        
        @media (max-width: 768px) {
            .main-grid { grid-template-columns: 1fr; }
            .form-row { grid-template-columns: 1fr; gap: 15px; }
            .stats-grid { grid-template-columns: repeat(2, 1fr); }
            .header-content { flex-direction: column; gap: 15px; text-align: center; }
            .nav-menu { flex-wrap: wrap; justify-content: center; }
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="header-content">
            <div class="header-title">
                <div class="header-logo">V7</div>
                <h1>🚀 Enhanced Admin Dashboard</h1>
            </div>
            <div class="nav-menu">
                <a href="/admin/analytics" class="nav-btn">📊 Analytics</a>
                <a href="/logout" class="nav-btn">🚪 Logout</a>
            </div>
        </div>
    </div>
    
    <div class="container">
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-number">{{ total_engineers }}</div>
                <div class="stat-label">Engineers</div>
                <div class="stat-trend trend-up">↗ Active Users</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ total_assignments }}</div>
                <div class="stat-label">Assessments</div>
                <div class="stat-trend trend-up">📈 Total Created</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ pending_reviews }}</div>
                <div class="stat-label">Pending Reviews</div>
                <div class="stat-trend trend-up">⏳ Need Attention</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ analytics_data.completion_rate }}%</div>
                <div class="stat-label">Completion Rate</div>
                <div class="stat-trend trend-up">✅ Success Rate</div>
            </div>
        </div>
        
        <div class="main-grid">
            <div class="card">
                <h2>🎯 Create Smart Assessment</h2>
                <form method="POST" action="/admin/create">
                    <div class="form-row">
                        <div class="form-group">
                            <label>Select Engineer</label>
                            <select name="engineer_id" required id="engineerSelect">
                                <option value="">Choose engineer...</option>
                                {{ eng_options }}
                            </select>
                        </div>
                        <div class="form-group">
                            <label>Assessment Topic</label>
                            <select name="topic" required>
                                <option value="">Select topic...</option>
                                <option value="sta">🕒 STA (Static Timing Analysis)</option>
                                <option value="cts">🌳 CTS (Clock Tree Synthesis)</option>
                                <option value="signoff">✅ Signoff Checks & Verification</option>
                            </select>
                        </div>
                        <button type="submit" class="btn-primary">Create Assessment</button>
                    </div>
                    <div class="analytics-preview">
                        <div class="analytics-item">
                            <span>📝 Questions Generated:</span>
                            <strong>18 (Adaptive Difficulty)</strong>
                        </div>
                        <div class="analytics-item">
                            <span>🤖 AI Scoring:</span>
                            <strong>Enabled</strong>
                        </div>
                        <div class="analytics-item">
                            <span>📊 Analytics Tracking:</span>
                            <strong>Full Coverage</strong>
                        </div>
                    </div>
                </form>
            </div>
            
            <div class="card">
                <h2>📋 Pending Reviews ({{ pending_reviews }})</h2>
                <div style="max-height: 400px; overflow-y: auto;">
                    {{ pending_html|safe }}
                </div>
            </div>
        </div>
        
        {% if analytics_data.topic_stats %}
        <div class="card" style="margin-top: 30px;">
            <h2>📈 Performance Analytics</h2>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px;">
                {% for stat in analytics_data.topic_stats %}
                <div class="analytics-item">
                    <div>
                        <span style="background: var(--primary); color: white; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; text-transform: uppercase;">{{ stat.topic }}</span>
                        <div style="margin-top: 8px;">
                            <strong>{{ stat.count }}</strong> submissions<br>
                            <strong>{{ stat.avg_score }}</strong> avg score
                        </div>
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>
        {% endif %}
    </div>
    
    <script>
        // Enhanced interactivity
        document.getElementById('engineerSelect').addEventListener('change', function() {
            const selectedOption = this.selectedOptions[0];
            const experience = selectedOption.getAttribute('data-exp');
            if (experience) {
                console.log(`Selected engineer with ${experience} years experience`);
            }
        });
        
        // Auto-refresh pending count every 30 seconds
        setInterval(() => {
            fetch('/admin/stats')
                .then(response => response.json())
                .then(data => {
                    console.log('Stats updated');
                })
                .catch(err => console.log('Stats update failed'));
        }, 30000);
    </script>
</body>
</html>""", 
    total_engineers=total_engineers,
    total_assignments=total_assignments,
    pending_reviews=pending_reviews,
    completed_reviews=completed_reviews,
    eng_options=eng_options,
    pending_html=pending_html,
    analytics_data=analytics_data
    )

@app.route('/admin/create', methods=['POST'])
def admin_create():
    if not session.get('is_admin'):
        return redirect('/login')
    
    engineer_id = request.form.get('engineer_id')
    topic = request.form.get('topic')
    
    if not engineer_id or not topic:
        return redirect('/admin')
    
    # Get engineer experience for adaptive questions
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('SELECT experience FROM users WHERE id = ?', (engineer_id,))
    engineer = c.fetchone()
    experience = engineer[0] if engineer else 3
    
    # Generate smart questions
    questions = question_generator.generate_smart_questions(topic, 18, experience)
    
    # Create assignment
    assignment_id = f"PD_{topic}_{engineer_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    due_date = (datetime.now() + timedelta(days=7)).isoformat()
    
    c.execute("""
        INSERT INTO assignments (id, engineer_id, topic, questions, created_date, due_date, created_by)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (assignment_id, engineer_id, topic, json.dumps(questions), 
          datetime.now().isoformat(), due_date, session['user_id']))
    
    conn.commit()
    conn.close()
    
    # Log analytics
    DatabaseManager.log_analytics('assignment_created', session['user_id'], {
        'assignment_id': assignment_id,
        'topic': topic,
        'engineer_id': engineer_id
    })
    
    return redirect('/admin')

@app.route('/admin/review/<assignment_id>', methods=['GET', 'POST'])
def admin_review(assignment_id):
    if not session.get('is_admin'):
        return redirect('/login')
    
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    # Get submission details
    c.execute('''
        SELECT s.*, a.topic, a.questions, u.display_name
        FROM submissions s
        JOIN assignments a ON s.assignment_id = a.id
        JOIN users u ON s.engineer_id = u.id
        WHERE s.assignment_id = ?
    ''', (assignment_id,))
    submission = c.fetchone()
    
    if not submission:
        conn.close()
        return redirect('/admin')
    
    # Process submission data
    answers = json.loads(submission[3])
    questions = json.loads(submission[12])
    auto_scores = json.loads(submission[6]) if submission[6] else {}
    
    # Handle grading submission
    if request.method == 'POST':
        manual_scores = {}
        feedback_notes = {}
        total_score = 0
        
        for i in range(len(questions)):
            manual_score = request.form.get(f'score_{i}', 0)
            feedback_note = request.form.get(f'feedback_{i}', '')
            try:
                score = float(manual_score)
                manual_scores[str(i)] = score
                feedback_notes[str(i)] = feedback_note
                total_score += score
            except:
                manual_scores[str(i)] = 0
        
        # Update submission with grades
        c.execute('''
            UPDATE submissions 
            SET manual_scores = ?, feedback = ?, total_score = ?, 
                status = 'graded', graded_by = ?, graded_date = ?
            WHERE assignment_id = ?
        ''', (json.dumps(manual_scores), json.dumps(feedback_notes), 
              total_score, session['user_id'], datetime.now().isoformat(), assignment_id))
        conn.commit()
        conn.close()
        
        # Log analytics
        DatabaseManager.log_analytics('submission_graded', session['user_id'], {
            'assignment_id': assignment_id,
            'total_score': total_score,
            'engineer_id': submission[2]
        })
        
        return redirect('/admin')
    
    conn.close()
    
    # Build review interface
    questions_html = ''
    for i, question in enumerate(questions):
        answer = answers.get(str(i), 'No answer provided')
        auto_score_data = auto_scores.get(str(i), {})
        suggested_score = auto_score_data.get('score', 0)
        
        # Enhanced scoring analysis
        if answer and answer != 'No answer provided':
            score_analysis = scoring_system.analyze_answer_comprehensive(question, answer, submission[11])
            suggested_score = score_analysis['score']
            breakdown = score_analysis['breakdown']
            suggestions = score_analysis['suggestions']
        else:
            breakdown = {"technical": 0, "depth": 0, "methodology": 0, "clarity": 0}
            suggestions = ["Answer not provided"]
        
        color = "#10b981" if suggested_score >= 7 else "#f59e0b# Enhanced PD Assessment System - Complete app.py for Railway
import os
import hashlib
import json
import random
import sqlite3
from datetime import datetime, timedelta
from threading import Lock
from flask import Flask, request, redirect, session, jsonify, render_template_string
import re

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'pd-secret-key-enhanced')

# Database setup
DATABASE = 'enhanced_assessments.db'
db_lock = Lock()

class DatabaseManager:
    @staticmethod
    def init_db():
        """Initialize SQLite database with enhanced schema"""
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        
        # Users table
        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE,
                display_name TEXT,
                email TEXT,
                password TEXT,
                is_admin BOOLEAN DEFAULT 0,
                experience INTEGER DEFAULT 3,
                department TEXT,
                created_date TEXT,
                last_login TEXT,
                theme TEXT DEFAULT 'light'
            )
        """)
        
        # Assignments table
        c.execute("""
            CREATE TABLE IF NOT EXISTS assignments (
                id TEXT PRIMARY KEY,
                engineer_id TEXT,
                topic TEXT,
                questions TEXT,
                created_date TEXT,
                due_date TEXT,
                status TEXT DEFAULT 'pending',
                difficulty_level INTEGER DEFAULT 1,
                max_points INTEGER DEFAULT 180,
                created_by TEXT,
                FOREIGN KEY (engineer_id) REFERENCES users (id)
            )
        """)
        
        # Submissions table (enhanced)
        c.execute("""
            CREATE TABLE IF NOT EXISTS submissions (
                id TEXT PRIMARY KEY,
                assignment_id TEXT,
                engineer_id TEXT,
                answers TEXT,
                submitted_date TEXT,
                status TEXT DEFAULT 'submitted',
                auto_scores TEXT,
                manual_scores TEXT,
                feedback TEXT,
                total_score INTEGER DEFAULT 0,
                graded_by TEXT,
                graded_date TEXT,
                time_spent INTEGER DEFAULT 0,
                FOREIGN KEY (assignment_id) REFERENCES assignments (id),
                FOREIGN KEY (engineer_id) REFERENCES users (id)
            )
        """)
        
        # Analytics table
        c.execute("""
            CREATE TABLE IF NOT EXISTS analytics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT,
                user_id TEXT,
                data TEXT,
                timestamp TEXT
            )
        """)
        
        conn.commit()
        conn.close()
    
    @staticmethod
    def log_analytics(event_type, user_id, data=None):
        """Log analytics events"""
        with db_lock:
            conn = sqlite3.connect(DATABASE)
            c = conn.cursor()
            c.execute("""
                INSERT INTO analytics (event_type, user_id, data, timestamp)
                VALUES (?, ?, ?, ?)
            """, (event_type, user_id, json.dumps(data) if data else None, datetime.now().isoformat()))
            conn.commit()
            conn.close()

# Enhanced Question Generation with Smart AI
class SmartQuestionGenerator:
    def __init__(self):
        self.question_templates = {
            "sta": [
                {
                    "template": "Your design has {violation_type} violations of {violation_amount}ps on {num_paths} critical paths. The design is running at {frequency}MHz. Analyze the root causes and propose {num_solutions} specific solutions with expected improvement estimates.",
                    "difficulty": 3,
                    "parameters": {
                        "violation_type": ["setup", "hold", "max_transition"],
                        "violation_amount": [20, 50, 100, 150, 200],
                        "num_paths": [10, 25, 50, 100, 200],
                        "frequency": [500, 800, 1000, 1500, 2000],
                        "num_solutions": [3, 4, 5]
                    }
                },
                {
                    "template": "Explain the concept of {concept} in static timing analysis. How does it impact {impact_area} and what are the industry-standard approaches to handle it in {technology_node} designs?",
                    "difficulty": 2,
                    "parameters": {
                        "concept": ["clock jitter", "OCV", "useful skew", "clock latency", "timing corners"],
                        "impact_area": ["setup timing", "hold timing", "power consumption", "area optimization"],
                        "technology_node": ["7nm", "5nm", "3nm", "advanced nodes"]
                    }
                },
                {
                    "template": "You're analyzing a {design_type} with {num_domains} clock domains running at different frequencies. Describe your approach to handle clock domain crossings and ensure timing closure across all interfaces.",
                    "difficulty": 4,
                    "parameters": {
                        "design_type": ["SoC", "CPU", "GPU", "AI accelerator"],
                        "num_domains": [3, 4, 5, 6]
                    }
                }
            ],
            "cts": [
                {
                    "template": "Design a clock tree for a {design_size} design with {num_flops} flip-flops distributed across {die_size}. The target skew is {target_skew}ps and you have {buffer_types} buffer types available. Explain your tree topology choice and optimization strategy.",
                    "difficulty": 3,
                    "parameters": {
                        "design_size": ["large-scale", "medium-scale", "complex"],
                        "num_flops": [10000, 25000, 50000, 100000],
                        "die_size": ["5mm x 5mm", "10mm x 10mm", "15mm x 15mm"],
                        "target_skew": [25, 50, 75, 100],
                        "buffer_types": [3, 4, 5, 6]
                    }
                },
                {
                    "template": "Your clock tree has {power_consumption}mW power consumption, which is {percentage}% of total chip power. Propose {num_techniques} specific techniques to reduce clock power while maintaining {skew_constraint}ps skew constraint.",
                    "difficulty": 4,
                    "parameters": {
                        "power_consumption": [50, 100, 150, 200],
                        "percentage": [15, 20, 25, 30, 35],
                        "num_techniques": [3, 4, 5],
                        "skew_constraint": [30, 50, 75]
                    }
                }
            ],
            "signoff": [
                {
                    "template": "Your design failed {check_type} with {num_violations} violations. The violations are distributed as: {violation_dist}. Create a systematic debugging and resolution plan with priority ordering and estimated effort.",
                    "difficulty": 3,
                    "parameters": {
                        "check_type": ["DRC", "LVS", "Antenna", "Metal Density"],
                        "num_violations": [50, 100, 200, 500],
                        "violation_dist": ["70% spacing, 20% width, 10% via", "50% density, 30% spacing, 20% antenna"]
                    }
                },
                {
                    "template": "Perform signoff analysis for a {design_type} in {technology} process. The design has {power_domains} power domains and {io_count} I/Os. List all required signoff checks and create a verification plan with timeline.",
                    "difficulty": 4,
                    "parameters": {
                        "design_type": ["automotive SoC", "mobile processor", "IoT chip", "high-performance CPU"],
                        "technology": ["7nm FinFET", "5nm", "3nm GAA"],
                        "power_domains": [2, 3, 4, 5],
                        "io_count": [100, 200, 500, 1000]
                    }
                }
            ]
        }
    
    def generate_smart_questions(self, topic, num_questions=18, engineer_exp=3):
        """Generate questions with adaptive difficulty"""
        templates = self.question_templates.get(topic, [])
        if not templates:
            return self._fallback_questions(topic)
        
        questions = []
        difficulty_distribution = self._get_difficulty_distribution(engineer_exp, num_questions)
        
        for target_difficulty in difficulty_distribution:
            suitable_templates = [t for t in templates if abs(t["difficulty"] - target_difficulty) <= 1]
            if not suitable_templates:
                suitable_templates = templates
            
            template = random.choice(suitable_templates)
            question = self._generate_from_template(template)
            questions.append(question)
        
        return questions[:num_questions]
    
    def _get_difficulty_distribution(self, engineer_exp, num_questions):
        """Create difficulty distribution based on experience"""
        if engineer_exp <= 2:
            easy_count = int(num_questions * 0.6)
            medium_count = int(num_questions * 0.3)
            hard_count = num_questions - easy_count - medium_count
            return [2] * easy_count + [3] * medium_count + [4] * hard_count
        elif engineer_exp <= 4:
            easy_count = int(num_questions * 0.3)
            medium_count = int(num_questions * 0.5)
            hard_count = num_questions - easy_count - medium_count
            return [2] * easy_count + [3] * medium_count + [4] * hard_count
        else:
            easy_count = int(num_questions * 0.2)
            medium_count = int(num_questions * 0.4)
            hard_count = num_questions - easy_count - medium_count
            return [2] * easy_count + [3] * medium_count + [4] * hard_count
    
    def _generate_from_template(self, template_data):
        """Generate question from template with random parameters"""
        template = template_data["template"]
        params = template_data["parameters"]
        
        generated_params = {}
        for param, options in params.items():
            generated_params[param] = random.choice(options)
        
        try:
            return template.format(**generated_params)
        except KeyError:
            return template
    
    def _fallback_questions(self, topic):
        """Fallback to static questions if smart generation fails"""
        fallback = {
            "sta": [
                "What is Static Timing Analysis and why is it critical in modern chip design?",
                "Explain setup and hold time violations. How do you debug and fix them?",
                "What is clock skew and how does it impact timing closure?",
                "Describe the concept of timing corners and their importance in analysis.",
                "How do you handle timing analysis for multiple clock domains?",
                "What are timing exceptions and when would you use false paths?",
                "Explain the difference between ideal clock and propagated clock analysis.",
                "What is clock jitter and how do you account for it in timing calculations?",
                "How do you analyze timing for memory interfaces and what makes them special?",
                "What is OCV (On-Chip Variation) and why do you add OCV margins in STA?",
                "Explain multicycle paths and give an example where you would use them.",
                "How do you handle timing analysis for generated clocks and clock dividers?",
                "What is clock domain crossing (CDC) and what timing checks are needed?",
                "Describe timing analysis for high-speed interfaces and their challenges.",
                "What reports do you check for timing signoff and why are they important?",
                "How do you ensure timing correlation between STA tools and silicon?",
                "What is useful skew and how can it help with timing closure?",
                "Explain timing optimization techniques for low-power designs."
            ],
            "cts": [
                "What is Clock Tree Synthesis and what are its main objectives?",
                "Explain different clock tree topologies and when to use each.",
                "How do you optimize clock trees for power consumption?",
                "What is useful skew and how can it help timing closure?",
                "Describe challenges in CTS for high-frequency designs.",
                "What is clock skew and what causes it in clock trees?",
                "How do you handle clock gating cells in clock tree synthesis?",
                "Explain the concept of clock insertion delay and how to minimize it.",
                "What are the trade-offs between H-tree and balanced tree topologies?",
                "How do you handle multiple clock domains in CTS?",
                "What is clock mesh and when would you choose it over tree topology?",
                "Describe clock tree optimization for process variation and yield.",
                "How do you build clock trees for multi-voltage designs?",
                "What is the typical CTS flow and when does it happen in the design cycle?",
                "How do you verify clock tree quality after synthesis?",
                "What are the challenges of clock tree synthesis in advanced nodes?",
                "Explain clock tree balancing and why it's important.",
                "How do you handle clock tree synthesis for low-power designs?"
            ],
            "signoff": [
                "What are the main signoff checks required before tape-out?",
                "Explain DRC violations and systematic approaches to fix them.",
                "What is LVS and how do you debug LVS mismatches?",
                "Describe IR drop analysis and mitigation techniques.",
                "How do you perform timing signoff for multi-corner analysis?",
                "What is antenna checking and why can violations damage your chip?",
                "Explain metal density rules and their impact on manufacturing.",
                "What is electromigration and how do you prevent EM violations?",
                "How do you perform signal integrity analysis during signoff?",
                "What is formal verification and how does it differ from simulation?",
                "Describe the signoff flow for advanced technology nodes.",
                "How do you coordinate signoff across different design teams?",
                "What additional checks are needed for multi-voltage designs?",
                "Explain thermal analysis and its importance in signoff.",
                "What is yield analysis and how do you optimize for manufacturing yield?",
                "How do you validate power delivery networks during signoff?",
                "What are the challenges of signoff in 7nm and below technologies?",
                "Describe the handoff process between design and manufacturing teams."
            ]
        }
        
        base_questions = fallback.get(topic, fallback["sta"])
        extended = []
        for i in range(18):
            base_q = base_questions[i % len(base_questions)]
            if i >= len(base_questions):
                extended.append(f"Advanced: {base_q}")
            else:
                extended.append(base_q)
        return extended

# Enhanced Scoring System
class EnhancedScoringSystem:
    def __init__(self):
        self.scoring_rubrics = {
            "sta": {
                "technical_terms": ["setup", "hold", "slack", "skew", "jitter", "corner", "violation", "closure"],
                "advanced_terms": ["ocv", "cppr", "useful skew", "clock latency", "propagated", "ideal"],
                "methodology_terms": ["debug", "optimize", "analyze", "systematic", "root cause"],
                "weights": {"technical": 0.4, "depth": 0.3, "methodology": 0.2, "clarity": 0.1}
            },
            "cts": {
                "technical_terms": ["clock tree", "skew", "insertion delay", "buffer", "topology", "synthesis"],
                "advanced_terms": ["h-tree", "mesh", "useful skew", "gating", "power optimization"],
                "methodology_terms": ["balance", "optimize", "strategy", "approach", "technique"],
                "weights": {"technical": 0.4, "depth": 0.3, "methodology": 0.2, "clarity": 0.1}
            },
            "signoff": {
                "technical_terms": ["drc", "lvs", "antenna", "density", "ir drop", "em", "signoff"],
                "advanced_terms": ["formal verification", "multi-corner", "yield analysis", "si analysis"],
                "methodology_terms": ["debug", "systematic", "flow", "process", "validation"],
                "weights": {"technical": 0.4, "depth": 0.3, "methodology": 0.2, "clarity": 0.1}
            }
        }
    
    def analyze_answer_comprehensive(self, question, answer, topic):
        """Comprehensive answer analysis with detailed feedback"""
        if not answer or len(answer.strip()) < 20:
            return {
                "score": 0,
                "breakdown": {"technical": 0, "depth": 0, "methodology": 0, "clarity": 0},
                "feedback": "Answer too short or empty",
                "suggestions": ["Provide more detailed technical explanation", "Include specific examples", "Explain methodology"]
            }
        
        rubric = self.scoring_rubrics.get(topic, self.scoring_rubrics["sta"])
        answer_lower = answer.lower()
        word_count = len(answer.split())
        
        # Technical accuracy score
        technical_score = self._score_technical_content(answer_lower, rubric)
        
        # Depth and detail score
        depth_score = self._score_depth(answer, word_count)
        
        # Methodology score
        methodology_score = self._score_methodology(answer_lower, rubric)
        
        # Clarity and structure score
        clarity_score = self._score_clarity(answer)
        
        # Weighted final score
        weights = rubric["weights"]
        final_score = (
            technical_score * weights["technical"] +
            depth_score * weights["depth"] +
            methodology_score * weights["methodology"] +
            clarity_score * weights["clarity"]
        ) * 10
        
        # Generate feedback and suggestions
        feedback, suggestions = self._generate_feedback(
            technical_score, depth_score, methodology_score, clarity_score, word_count
        )
        
        return {
            "score": round(final_score, 1),
            "breakdown": {
                "technical": round(technical_score * 10, 1),
                "depth": round(depth_score * 10, 1),
                "methodology": round(methodology_score * 10, 1),
                "clarity": round(clarity_score * 10, 1)
            },
            "feedback": feedback,
            "suggestions": suggestions,
            "word_count": word_count
        }
    
    def _score_technical_content(self, answer_lower, rubric):
        tech_terms = sum(1 for term in rubric["technical_terms"] if term in answer_lower)
        advanced_terms = sum(1 for term in rubric["advanced_terms"] if term in answer_lower)
        
        tech_score = min(tech_terms / 3, 1.0)
        advanced_score = min(advanced_terms / 2, 0.5)
        
        return min(tech_score + advanced_score, 1.0)
    
    def _score_depth(self, answer, word_count):
        word_score = min(word_count / 100, 0.7)
        
        has_examples = any(marker in answer.lower() for marker in ['example', 'for instance', 'such as'])
        has_numbers = bool(re.search(r'\d+', answer))
        has_comparisons = any(marker in answer.lower() for marker in ['compare', 'versus', 'vs', 'better', 'worse'])
        
        structure_score = (has_examples * 0.1) + (has_numbers * 0.1) + (has_comparisons * 0.1)
        
        return min(word_score + structure_score, 1.0)
    
    def _score_methodology(self, answer_lower, rubric):
        method_terms = sum(1 for term in rubric["methodology_terms"] if term in answer_lower)
        
        has_steps = any(marker in answer_lower for marker in ['step', 'first', 'second', 'then', 'next', 'finally'])
        has_process = any(marker in answer_lower for marker in ['process', 'flow', 'procedure', 'approach'])
        
        method_score = min(method_terms / 2, 0.7)
        process_score = (has_steps * 0.15) + (has_process * 0.15)
        
        return min(method_score + process_score, 1.0)
    
    def _score_clarity(self, answer):
        sentences = answer.split('.')
        avg_sentence_length = sum(len(s.split()) for s in sentences) / max(len(sentences), 1)
        
        length_score = 1.0 - abs(avg_sentence_length - 17.5) / 17.5
        length_score = max(0, min(length_score, 1.0))
        
        has_organization = any(marker in answer.lower() for marker in [':', '-', '1.', '2.', 'bullet'])
        org_score = 0.3 if has_organization else 0
        
        return min(length_score * 0.7 + org_score, 1.0)
    
    def _generate_feedback(self, tech_score, depth_score, method_score, clarity_score, word_count):
        feedback_parts = []
        suggestions = []
        
        if tech_score >= 0.8:
            feedback_parts.append("Strong technical knowledge demonstrated")
        elif tech_score >= 0.6:
            feedback_parts.append("Good technical understanding shown")
            suggestions.append("Include more specific technical terminology")
        else:
            feedback_parts.append("Limited technical content")
            suggestions.append("Use more industry-specific technical terms")
        
        if depth_score >= 0.8:
            feedback_parts.append("comprehensive analysis provided")
        elif depth_score >= 0.6:
            feedback_parts.append("adequate detail level")
            suggestions.append("Provide more detailed explanations and examples")
        else:
            feedback_parts.append("needs more depth")
            suggestions.append("Expand with specific examples and quantitative details")
        
        if method_score >= 0.7:
            feedback_parts.append("clear methodology described")
        else:
            feedback_parts.append("methodology could be clearer")
            suggestions.append("Describe step-by-step approach or process")
        
        if word_count < 50:
            suggestions.append("Increase answer length for better coverage")
        elif word_count > 300:
            suggestions.append("Consider more concise explanations")
        
        feedback = ", ".join(feedback_parts).capitalize() + f" ({word_count} words)"
        
        return feedback, suggestions

# Initialize components
DatabaseManager.init_db()
question_generator = SmartQuestionGenerator()
scoring_system = EnhancedScoringSystem()

# User authentication functions
def hash_pass(pwd):
    return hashlib.sha256(pwd.encode()).hexdigest()

def check_pass(hashed, pwd):
    return hashed == hashlib.sha256(pwd.encode()).hexdigest()

def init_data():
    """Initialize demo data"""
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    # Check if admin exists
    c.execute('SELECT id FROM users WHERE id = ?', ('admin',))
    if not c.fetchone():
        # Create admin
        c.execute("""
            INSERT INTO users (id, username, display_name, email, password, is_admin, experience, created_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, ('admin', 'admin', 'System Administrator', 'admin@vibhuayu.com', 
              hash_pass('Vibhuaya@3006'), 1, 5, datetime.now().isoformat()))
        
        # Create 18 engineers
        engineer_data = [
            ('eng001', 'Kranthi', 'kranthi@vibhuayu.com', 3),
            ('eng002', 'Neela', 'neela@vibhuayu.com', 4),
            ('eng003', 'Bhanu', 'bhanu@vibhuayu.com', 2),
            ('eng004', 'Lokeshwari', 'lokeshwari@vibhuayu.com', 5),
            ('eng005', 'Nagesh', 'nagesh@vibhuayu.com', 3),
            ('eng006', 'VJ', 'vj@vibhuayu.com', 4),
            ('eng007', 'Pravalika', 'pravalika@vibhuayu.com', 2),
            ('eng008', 'Daniel', 'daniel@vibhuayu.com', 6),
            ('eng009', 'Karthik', 'karthik@vibhuayu.com', 3),
            ('eng010', 'Hema', 'hema@vibhuayu.com', 4),
            ('eng011', 'Naveen', 'naveen@vibhuayu.com', 5),
            ('eng012', 'Srinivas', 'srinivas@vibhuayu.com', 3),
            ('eng013', 'Meera', 'meera@vibhuayu.com', 2),
            ('eng014', 'Suraj', 'suraj@vibhuayu.com', 4),
            ('eng015', 'Akhil', 'akhil@vibhuayu.com', 3),
            ('eng016', 'Vikas', 'vikas@vibhuayu.com', 5),
            ('eng017', 'Sahith', 'sahith@vibhuayu.com', 2),
            ('eng018', 'Sravan', 'sravan@vibhuayu.com', 4)
        ]
        
        for uid, name, email, exp in engineer_data:
            c.execute("""
                INSERT INTO users (id, username, display_name, email, password, is_admin, experience, department, created_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (uid, uid, name, email, hash_pass('password123'), 0, exp, 'Physical Design', datetime.now().isoformat()))
    
    conn.commit()
    conn.close()

def _time_ago(date_str):
    """Calculate time ago from date string"""
    try:
        date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        now = datetime.now()
        diff = now - date_obj
        
        if diff.days > 0:
            return f"{diff.days}d ago"
        elif diff.seconds > 3600:
            return f"{diff.seconds // 3600}h ago"
        elif diff.seconds > 60:
            return f"{diff.seconds // 60}m ago"
        else:
            return "Just now"
    except:
        return "Unknown"

# Routes
@app.route('/')
def home():
    if 'user_id' in session:
        if session.get('is_admin'):
            return redirect('/admin')
        return redirect('/student')
    return redirect('/login')

@app.route('/health')
def health():
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE username = ?', (username,))
        user = c.fetchone()
        conn.close()
        
        if user and check_pass(user[4], password):
            session['user_id'] = user[0]
            session['username'] = user[1]
            session['display_name'] = user[2]
            session['is_admin'] = bool(user[5])
            session['theme'] = user[10] if user[10] else 'light'
            
            # Update last login
            conn = sqlite3.connect(DATABASE)
            c = conn.cursor()
            c.execute('UPDATE users SET last_login = ? WHERE id = ?', 
                     (datetime.now().isoformat(), user[0]))
            conn.commit()
            conn.close()
            
            # Log analytics
            DatabaseManager.log_analytics('login', user[0])
            
            if bool(user[5]):
                return redirect('/admin')
            return redirect('/student')
    
    # Enhanced login page
    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
    <title>Vibhuayu Technologies - Enhanced PD Assessment</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        :root {
            --primary-color: #667eea;
            --secondary-color: #764ba2;
            --success-color: #10b981;
            --warning-color: #f59e0b;
            --error-color: #ef4444;
            --bg-primary: #0f172a;
            --bg-secondary: #1e293b;
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --surface: rgba(255, 255, 255, 0.98);
            --border: #e2e8f0;
        }
        
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            background: linear-gradient(135deg, var(--bg-primary) 0%, var(--bg-secondary) 100%); 
            min-height: 100vh; 
            display: flex; 
            align-items: center; 
            justify-content: center; 
            position: relative;
            overflow-x: hidden;
        }
        
        body::before {
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0; bottom: 0;
            background: 
                radial-gradient(circle at 30% 40%, rgba(102, 126, 234, 0.3) 0%, transparent 50%),
                radial-gradient(circle at 80% 80%, rgba(118, 75, 162, 0.15) 0%, transparent 50%);
            z-index: 1;
        }
        
        .container {
            position: relative; z-index: 2;
            background: var(--surface);
            backdrop-filter: blur(20px);
            border-radius: 24px;
            padding: 50px 40px;
            width: min(450px, 90vw);
            box-shadow: 0 25px 50px rgba(0, 0, 0, 0.25);
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        .logo-section {
            text-align: center;
            margin-bottom: 35px;
        }
        
        .logo {
            width: 80px; height: 80px;
            margin: 0 auto 20px;
            background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
            border-radius: 20px;
            display: flex; align-items: center; justify-content: center;
            color: white; font-size: 36px; font-weight: 900;
            box-shadow: 0 10px 30px rgba(102, 126, 234, 0.3);
            position: relative; overflow: hidden;
        }
" if suggested_score >= 5 else "#ef4444"
        
        questions_html += f'''
        <div class="question-review-card">
            <div class="question-header">
                <h3>Question {i+1}</h3>
                <div class="ai-score-badge" style="background: {color};">
                    AI Score: {suggested_score}/10
                </div>
            </div>
            
            <div class="question-text">
                <strong>Question:</strong><br>
                {question}
            </div>
            
            <div class="answer-section">
                <strong>Engineer's Answer:</strong>
                <div class="answer-text">{answer}</div>
            </div>
            
            <div class="scoring-analysis">
                <div class="score-breakdown">
                    <h4>AI Analysis Breakdown:</h4>
                    <div class="breakdown-grid">
                        <div class="breakdown-item">
                            <span>Technical:</span>
                            <span>{breakdown['technical']}/10</span>
                        </div>
                        <div class="breakdown-item">
                            <span>Depth:</span>
                            <span>{breakdown['depth']}/10</span>
                        </div>
                        <div class="breakdown-item">
                            <span>Methodology:</span>
                            <span>{breakdown['methodology']}/10</span>
                        </div>
                        <div class="breakdown-item">
                            <span>Clarity:</span>
                            <span>{breakdown['clarity']}/10</span>
                        </div>
                    </div>
                </div>
                
                <div class="ai-suggestions">
                    <h4>Improvement Suggestions:</h4>
                    <ul>
                        {''.join([f'<li>{suggestion}</li>' for suggestion in suggestions[:3]])}
                    </ul>
                </div>
            </div>
            
            <div class="manual-grading">
                <div class="grade-input">
                    <label>Your Score:</label>
                    <input type="number" name="score_{i}" min="0" max="10" step="0.1" 
                           value="{suggested_score}" class="score-input">
                    <button type="button" onclick="this.previousElementSibling.value='{suggested_score}'" 
                            class="use-ai-btn">Use AI Score</button>
                </div>
                <div class="feedback-input">
                    <label>Additional Feedback:</label>
                    <textarea name="feedback_{i}" placeholder="Optional: Add specific feedback for this answer..."></textarea>
                </div>
            </div>
        </div>'''
    
    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
    <title>Review Assessment - Enhanced Admin</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        :root {
            --primary: #667eea;
            --secondary: #764ba2;
            --success: #10b981;
            --warning: #f59e0b;
            --error: #ef4444;
            --surface: #ffffff;
            --bg-light: #f8fafc;
        }
        
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
            min-height: 100vh;
        }
        
        .header {
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            color: white; padding: 20px 0;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
        }
        
        .header-content {
            max-width: 1200px; margin: 0 auto; padding: 0 20px;
            display: flex; justify-content: space-between; align-items: center;
        }
        
        .container {
            max-width: 1200px; margin: 20px auto; padding: 0 20px;
        }
        
        .submission-info {
            background: var(--surface); border-radius: 16px;
            padding: 25px; margin-bottom: 25px;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
        }
        
        .info-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
        }
        
        .info-item {
            text-align: center;
        }
        
        .info-value {
            font-size: 24px; font-weight: 700;
            color: var(--primary); margin-bottom: 5px;
        }
        
        .info-label {
            color: #64748b; font-size: 14px; font-weight: 600;
        }
        
        .question-review-card {
            background: var(--surface); border-radius: 16px;
            padding: 25px; margin: 20px 0;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
            border-left: 4px solid var(--primary);
        }
        
        .question-header {
            display: flex; justify-content: space-between;
            align-items: center; margin-bottom: 20px;
        }
        
        .question-header h3 {
            color: #1e293b; font-size: 18px;
        }
        
        .ai-score-badge {
            color: white; padding: 6px 15px;
            border-radius: 20px; font-weight: 600; font-size: 14px;
        }
        
        .question-text {
            background: var(--bg-light); padding: 15px;
            border-radius: 8px; margin-bottom: 15px;
            border-left: 3px solid var(--primary);
        }
        
        .answer-section {
            margin-bottom: 20px;
        }
        
        .answer-text {
            background: #fefefe; border: 1px solid #e2e8f0;
            padding: 15px; border-radius: 8px; margin-top: 8px;
            line-height: 1.6; white-space: pre-wrap;
            max-height: 200px; overflow-y: auto;
        }
        
        .scoring-analysis {
            background: var(--bg-light); border-radius: 12px;
            padding: 20px; margin-bottom: 20px;
        }
        
        .breakdown-grid {
            display: grid; grid-template-columns: repeat(2, 1fr);
            gap: 10px; margin-top: 10px;
        }
        
        .breakdown-item {
            display: flex; justify-content: space-between;
            padding: 8px 12px; background: white; border-radius: 6px;
        }
        
        .ai-suggestions {
            margin-top: 15px;
        }
        
        .ai-suggestions ul {
            margin-top: 8px; padding-left: 20px;
        }
        
        .ai-suggestions li {
            margin-bottom: 5px; color: #64748b;
        }
        
        .manual-grading {
            display: grid; grid-template-columns: 1fr 2fr; gap: 20px;
            padding-top: 20px; border-top: 1px solid #e2e8f0;
        }
        
        .grade-input {
            display: flex; flex-direction: column; gap: 10px;
        }
        
        .score-input {
            padding: 8px 12px; border: 2px solid #e2e8f0;
            border-radius: 6px; font-size: 16px; width: 80px;
        }
        
        .use-ai-btn {
            padding: 6px 12px; background: var(--primary);
            color: white; border: none; border-radius: 6px;
            cursor: pointer; font-size: 12px;
        }
        
        .feedback-input textarea {
            width: 100%; height: 80px; padding: 10px;
            border: 2px solid #e2e8f0; border-radius: 6px;
            resize: vertical; font-family: inherit;
        }
        
        .submit-section {
            background: var(--surface); border-radius: 16px;
            padding: 25px; margin-top: 30px; text-align: center;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
        }
        
        .btn {
            padding: 12px 25px; border: none; border-radius: 8px;
            font-weight: 600; cursor: pointer; margin: 5px;
            text-decoration: none; display: inline-block;
            transition: all 0.3s ease;
        }
        
        .btn-primary {
            background: linear-gradient(135deg, var(--success), #059669);
            color: white;
        }
        
        .btn-secondary {
            background: #6b7280; color: white;
        }
        
        .btn:hover { transform: translateY(-2px); }
        
        .total-calculator {
            background: var(--primary); color: white;
            padding: 15px; border-radius: 12px; margin-bottom: 20px;
            text-align: center; font-weight: 600;
        }
        
        @media (max-width: 768px) {
            .manual-grading { grid-template-columns: 1fr; }
            .breakdown-grid { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="header-content">
            <h1>📝 Review Assessment</h1>
            <a href="/admin" class="btn btn-secondary">← Back to Dashboard</a>
        </div>
    </div>
    
    <div class="container">
        <div class="submission-info">
            <div class="info-grid">
                <div class="info-item">
                    <div class="info-value">{{ submission[13] }}</div>
                    <div class="info-label">Engineer</div>
                </div>
                <div class="info-item">
                    <div class="info-value">{{ submission[11].upper() }}</div>
                    <div class="info-label">Topic</div>
                </div>
                <div class="info-item">
                    <div class="info-value">{{ len(questions) }}</div>
                    <div class="info-label">Questions</div>
                </div>
                <div class="info-item">
                    <div class="info-value">{{ submission[4][:10] }}</div>
                    <div class="info-label">Submitted</div>
                </div>
            </div>
        </div>
        
        <form method="POST" id="gradingForm">
            <div class="total-calculator">
                <span>Total Score: </span>
                <span id="totalScore">0</span>
                <span>/{{ len(questions) * 10 }} points</span>
                <span style="margin-left: 20px;">Average: </span>
                <span id="averageScore">0.0</span>
                <span>/10</span>
            </div>
            
            {{ questions_html|safe }}
            
            <div class="submit-section">
                <div style="background: #fef3c7; padding: 15px; border-radius: 8px; margin-bottom: 20px; color: #92400e;">
                    ⚠️ <strong>Review carefully:</strong> Grades will be final once submitted.
                </div>
                <button type="submit" class="btn btn-primary">✅ Submit Final Grades</button>
                <a href="/admin" class="btn btn-secondary">Cancel Review</a>
            </div>
        </form>
    </div>
    
    <script>
        // Calculate total score dynamically
        function updateTotal() {
            const scoreInputs = document.querySelectorAll('.score-input');
            let total = 0;
            let count = 0;
            
            scoreInputs.forEach(input => {
                const value = parseFloat(input.value) || 0;
                total += value;
                count++;
            });
            
            document.getElementById('totalScore').textContent = total.toFixed(1);
            document.getElementById('averageScore').textContent = (total / count).toFixed(1);
        }
        
        // Add event listeners to all score inputs
        document.querySelectorAll('.score-input').forEach(input => {
            input.addEventListener('input', updateTotal);
        });
        
        // Initial calculation
        updateTotal();
        
        // Form validation
        document.getElementById('gradingForm').addEventListener('submit', function(e) {
            if (!confirm('Are you sure you want to submit these grades? This action cannot be undone.')) {
                e.preventDefault();
            }
        });
    </script>
</body>
</html>""", 
    submission=submission,
    questions=questions,
    answers=answers,
    auto_scores=auto_scores,
    questions_html=questions_html
    )

@app.route('/admin/analytics')
def admin_analytics():
    if not session.get('is_admin'):
        return redirect('/login')
    
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    # Comprehensive analytics queries
    analytics_data = {}
    
    # Topic performance
    c.execute('''
        SELECT 
            a.topic,
            COUNT(s.id) as submissions,
            AVG(CAST(s.total_score as FLOAT)) as avg_score,
            MAX(CAST(s.total_score as FLOAT)) as max_score,
            MIN(CAST(s.total_score as FLOAT)) as min_score
        FROM assignments a
        LEFT JOIN submissions s ON a.id = s.assignment_id AND s.status = 'graded'
        GROUP BY a.topic
    ''')
    analytics_data['topic_performance'] = c.fetchall()
    
    # Engineer performance
    c.execute('''
        SELECT 
            u.display_name,
            u.experience,
            COUNT(s.id) as completed,
            AVG(CAST(s.total_score as FLOAT)) as avg_score,
            MAX(CAST(s.total_score as FLOAT)) as best_score
        FROM users u
        LEFT JOIN submissions s ON u.id = s.engineer_id AND s.status = 'graded'
        WHERE u.is_admin = 0
        GROUP BY u.id
        ORDER BY avg_score DESC
    ''')
    analytics_data['engineer_performance'] = c.fetchall()
    
    conn.close()
    
    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
    <title>Performance Analytics - Enhanced Admin</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.9.1/chart.min.js"></script>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
            margin: 0; min-height: 100vh; color: white;
        }
        
        .analytics-container {
            max-width: 1400px; margin: 0 auto; padding: 20px;
        }
        
        .analytics-grid {
            display: grid; grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 25px; margin: 25px 0;
        }
        
        .chart-card {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 20px; padding: 25px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
        }
        
        .chart-title {
            color: #1e293b; font-size: 18px; font-weight: 700;
            margin-bottom: 20px; text-align: center;
        }
        
        .stats-overview {
            display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px; margin-bottom: 30px;
        }
        
        .stat-box {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 16px; padding: 20px; text-align: center;
            backdrop-filter: blur(10px);
        }
        
        .stat-number {
            font-size: 32px; font-weight: 800; margin-bottom: 5px;
        }
        
        .performance-table {
            width: 100%; border-collapse: collapse; margin-top: 15px;
        }
        
        .performance-table th,
        .performance-table td {
            padding: 12px; text-align: left; border-bottom: 1px solid #e2e8f0;
        }
        
        .performance-table th {
            background: #f8fafc; font-weight: 600; color: #1e293b;
        }
        
        .score-badge {
            padding: 4px 12px; border-radius: 20px; font-weight: 600;
            font-size: 12px; color: white;
        }
        
        .score-excellent { background: #10b981; }
        .score-good { background: #f59e0b; }
        .score-needs-improvement { background: #ef4444; }
    </style>
</head>
<body>
    <div class="analytics-container">
        <div style="text-align: center; margin-bottom: 30px;">
            <h1 style="font-size: 36px; margin-bottom: 10px;">📊 Performance Analytics</h1>
            <p style="color: #94a3b8;">Comprehensive insights into assessment performance</p>
            <a href="/admin" style="color: #667eea; text-decoration: none;">← Back to Dashboard</a>
        </div>
        
        <div class="stats-overview">
            <div class="stat-box">
                <div class="stat-number" style="color: #667eea;">{{ analytics_data.topic_performance|length }}</div>
                <div>Active Topics</div>
            </div>
            <div class="stat-box">
                <div class="stat-number" style="color: #10b981;">{{ analytics_data.engineer_performance|length }}</div>
                <div>Engineers</div>
            </div>
            <div class="stat-box">
                <div class="stat-number" style="color: #f59e0b;">
                    {% set total_submissions = analytics_data.topic_performance|map(attribute=1)|sum %}
                    {{ total_submissions }}
                </div>
                <div>Total Submissions</div>
            </div>
            <div class="stat-box">
                <div class="stat-number" style="color: #8b5cf6;">
                    {% if analytics_data.topic_performance %}
                        {% set avg_score = (analytics_data.topic_performance|map(attribute=2)|sum) / (analytics_data.topic_performance|length) %}
                        {{ "%.1f"|format(avg_score) }}
                    {% else %}
                        0.0
                    {% endif %}
                </div>
                <div>Average Score</div>
            </div>
        </div>
        
        <div class="analytics-grid">
            <div class="chart-card">
                <div class="chart-title">📈 Topic Performance Overview</div>
                <canvas id="topicChart" width="400" height="300"></canvas>
            </div>
            
            <div class="chart-card">
                <div class="chart-title">👥 Engineer Performance Distribution</div>
                <canvas id="engineerChart" width="400" height="300"></canvas>
            </div>
        </div>
        
        <div class="chart-card">
            <div class="chart-title">🏆 Top Performers</div>
            <table class="performance-table">
                <thead>
                    <tr>
                        <th>Engineer</th>
                        <th>Experience</th>
                        <th>Completed</th>
                        <th>Average Score</th>
                        <th>Best Score</th>
                        <th>Performance</th>
                    </tr>
                </thead>
                <tbody>
                    {% for engineer in analytics_data.engineer_performance[:10] %}
                    <tr>
                        <td><strong>{{ engineer[0] }}</strong></td>
                        <td>{{ engineer[1] }}y</td>
                        <td>{{ engineer[2] }}</td>
                        <td>{{ "%.1f"|format(engineer[3] or 0) }}</td>
                        <td>{{ "%.1f"|format(engineer[4] or 0) }}</td>
                        <td>
                            {% set avg = engineer[3] or 0 %}
                            {% if avg >= 8 %}
                                <span class="score-badge score-excellent">Excellent</span>
                            {% elif avg >= 6 %}
                                <span class="score-badge score-good">Good</span>
                            {% else %}
                                <span class="score-badge score-needs-improvement">Needs Improvement</span>
                            {% endif %}
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
    
    <script>
        // Topic Performance Chart
        const topicData = {{ analytics_data.topic_performance|tojson }};
        const topicLabels = topicData.map(item => item[0].toUpperCase());
        const topicScores = topicData.map(item => item[2] || 0);
        
        new Chart(document.getElementById('topicChart'), {
            type: 'bar',
            data: {
                labels: topicLabels,
                datasets: [{
                    label: 'Average Score',
                    data: topicScores,
                    backgroundColor: ['#667eea', '#10b981', '#f59e0b'],
                    borderColor: ['#4f46e5', '#059669', '#d97706'],
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 10,
                        title: { display: true, text: 'Average Score' }
                    }
                }
            }
        });
        
        // Engineer Performance Distribution
        const engineerData = {{ analytics_data.engineer_performance|tojson }};
        const performanceBuckets = [0, 0, 0]; // [0-5, 5-7.5, 7.5-10]
        
        engineerData.forEach(engineer => {
            const score = engineer[3] || 0;
            if (score < 5) performanceBuckets[0]++;
            else if (score < 7.5) performanceBuckets[1]++;
            else performanceBuckets[2]++;
        });
        
        new Chart(document.getElementById('engineerChart'), {
            type: 'doughnut',
            data: {
                labels: ['Needs Improvement (0-5)', 'Good (5-7.5)', 'Excellent (7.5-10)'],
                datasets: [{
                    data: performanceBuckets,
                    backgroundColor: ['#ef4444', '#f59e0b', '#10b981'],
                    borderWidth: 2,
                    borderColor: '#fff'
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { position: 'bottom' }
                }
            }
        });
    </script>
</body>
</html>""", analytics_data=analytics_data)

@app.route('/student')
def student():
    if not session.get('user_id') or session.get('is_admin'):
        return redirect('/login')
    
    user_id = session['user_id']
    
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    # Get user details
    c.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    user = c.fetchone()
    
    # Get user's assignments
    c.execute('''
        SELECT a.*, s.status as submission_status, s.total_score, s.submitted_date
        FROM assignments a
        LEFT JOIN submissions s ON a.id = s.assignment_id AND a.engineer_id = s.engineer_id
        WHERE a.engineer_id = ?
        ORDER BY a.created_date DESC
    ''', (user_id,))
    assignments = c.fetchall()
    
    conn.close()
    
    # Build assignments HTML
    assignments_html = ''
    for assignment in assignments:
        status = assignment[11] or 'pending'
        score = assignment[12] or 0
        
        if status == 'graded':
            assignments_html += f'''
            <div class="assignment-card completed">
                <div class="assignment-header">
                    <h3>✅ {assignment[2].upper()} Assessment</h3>
                    <div class="score-display">{score}/180</div>
                </div>
                <div class="assignment-meta">
                    📊 Completed on {assignment[13][:10] if assignment[13] else 'Unknown'} | 
                    🎯 Score: {score} points
                </div>
                <div class="status-badge completed">Assessment Completed</div>
            </div>'''
        elif status == 'submitted':
            assignments_html += f'''
            <div class="assignment-card submitted">
                <div class="assignment-header">
                    <h3>⏳ {assignment[2].upper()} Assessment</h3>
                    <div class="status-display">Under Review</div>
                </div>
                <div class="assignment-meta">
                    📝 Submitted on {assignment[13][:10] if assignment[13] else 'Unknown'} | 
                    ⏰ Awaiting grades
                </div>
                <div class="status-badge submitted">Under Review</div>
            </div>'''
        else:
            assignments_html += f'''
            <div class="assignment-card pending">
                <div class="assignment-header">
                    <h3>🎯 {assignment[2].upper()} Assessment</h3>
                    <div class="due-date">Due: {assignment[5][:10]}</div>
                </div>
                <div class="assignment-meta">
                    📋 18 Smart Questions | 🎖️ Max: 180 points | 
                    ⏰ Due: {assignment[5][:10]}
                </div>
                <a href="/student/test/{assignment[0]}" class="start-btn">Start Assessment</a>
            </div>'''
    
    if not assignments_html:
        assignments_html = '''
        <div class="no-assignments">
            <div class="empty-icon">📭</div>
            <h3>No Assessments Yet</h3>
            <p>Your administrator will assign assessments soon. Check back later!</p>
        </div>'''
    
    # Calculate stats
    total_assignments = len(assignments)
    completed = len([a for a in assignments if (a[11] == 'graded')])
    pending = len([a for a in assignments if not a[11] or a[11] == 'pending'])
    avg_score = sum([a[12] for a in assignments if a[12]]) / max(completed, 1) if completed > 0 else 0
    
    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
    <title>Enhanced Engineer Dashboard - {{ user[2] }}</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        :root {
            --primary: #667eea;
            --secondary: #764ba2;
            --success: #10b981;
            --warning: #f59e0b;
            --error: #ef4444;
            --surface: rgba(255, 255, 255, 0.95);
            --text-primary: #1e293b;
            --text-secondary: #64748b;
        }
        
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%);
            min-height: 100vh;
        }
        
        .header {
            background: rgba(255,255,255,0.15);
            backdrop-filter: blur(20px);
            color: white; padding: 25px 0;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
        }
        
        .header-content {
            max-width: 1200px; margin: 0 auto; padding: 0 20px;
            display: flex; justify-content: space-between; align-items: center;
        }
        
        .user-info {
            display: flex; align-items: center; gap: 15px;
        }
        
        .user-avatar {
            width: 50px; height: 50px;
            background: rgba(255,255,255,0.2);
            border-radius: 50%; display: flex; align-items: center; justify-content: center;
            font-weight: 900; font-size: 20px;
            backdrop-filter: blur(10px);
        }
        
        .welcome-text h1 {
            font-size: 24px; font-weight: 700; margin-bottom: 5px;
        }
        
        .welcome-text p {
            opacity: 0.9; font-size: 14px;
        }
        
        .nav-actions {
            display: flex; gap: 15px;
        }
        
        .nav-btn {
            background: rgba(255,255,255,0.2);
            color: white; padding: 10px 15px;
            text-decoration: none; border-radius: 8px;
            backdrop-filter: blur(10px); transition: all 0.3s ease;
            font-weight: 600; font-size: 14px;
        }
        
        .nav-btn:hover {
            background: rgba(255,255,255,0.3);
            transform: translateY(-2px);
        }
        
        .container {
            max-width: 1200px; margin: 30px auto; padding: 0 20        
        .logo::before {
            content: ''; position: absolute;
            top: 0; left: 0; right: 0; bottom: 0;
            background: linear-gradient(45deg, transparent 30%, rgba(255,255,255,0.1) 50%, transparent 70%);
            transform: translateX(-100%);
            animation: shine 3s infinite;
        }
        
        @keyframes shine {
            0% { transform: translateX(-100%); }
            50% { transform: translateX(100%); }
            100% { transform: translateX(100%); }
        }
        
        .title {
            font-size: 28px; font-weight: 700;
            background: linear-gradient(135deg, #1e293b, #475569);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            margin-bottom: 8px;
        }
        
        .subtitle {
            color: #64748b; font-size: 16px; font-weight: 500;
            margin-bottom: 35px;
        }
        
        .form-group {
            margin-bottom: 24px;
        }
        
        .form-group label {
            display: block; margin-bottom: 8px;
            color: #374151; font-weight: 600; font-size: 14px;
        }
        
        .form-input {
            width: 100%; padding: 16px 20px;
            border: 2px solid var(--border);
            border-radius: 12px; font-size: 16px;
            transition: all 0.3s ease;
            background: rgba(255, 255, 255, 0.8);
        }
        
        .form-input:focus {
            outline: none; border-color: var(--primary-color);
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
            background: white;
        }
        
        .login-btn {
            width: 100%; padding: 16px;
            background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
            color: white; border: none; border-radius: 12px;
            font-size: 16px; font-weight: 600; cursor: pointer;
            transition: all 0.3s ease; margin-bottom: 30px;
        }
        
        .login-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 25px rgba(102, 126, 234, 0.4);
        }
        
        .info-card {
            background: linear-gradient(135deg, #f8fafc, #f1f5f9);
            border: 1px solid var(--border);
            border-radius: 16px; padding: 24px; text-align: center;
        }
        
        .credentials {
            background: white; border-radius: 8px; padding: 12px;
            margin: 12px 0; border-left: 4px solid var(--primary-color);
        }
        
        .feature-highlights {
            margin-top: 15px; font-size: 12px; color: #64748b;
            line-height: 1.6;
        }
        
        .new-badge {
            background: var(--success-color); color: white;
            padding: 2px 6px; border-radius: 10px;
            font-size: 10px; font-weight: 600; margin-left: 5px;
        }
        
        @media (max-width: 480px) {
            .container { padding: 30px 20px; }
            .title { font-size: 24px; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="logo-section">
            <div class="logo">V7</div>
            <div class="title">Enhanced PD Portal</div>
            <div class="subtitle">Advanced Assessment & Analytics System</div>
        </div>
        
        <form method="POST">
            <div class="form-group">
                <label>Username</label>
                <input type="text" name="username" class="form-input" 
                       placeholder="Enter your username" required autocomplete="username">
            </div>
            <div class="form-group">
                <label>Password</label>
                <input type="password" name="password" class="form-input" 
                       placeholder="Enter your password" required autocomplete="current-password">
            </div>
            <button type="submit" class="login-btn">Access Enhanced Portal</button>
        </form>
        
        <div class="info-card">
            <div style="font-weight: 700; margin-bottom: 16px;">🔐 Demo Credentials</div>
            <div class="credentials">
                <strong>Engineers:</strong> eng001 through eng018<br>
                <strong>Password:</strong> password123<br>
                <strong>Admin:</strong> admin / Vibhuaya@3006
            </div>
            <div class="feature-highlights">
                <strong>🚀 New Features:</strong><br>
                Smart Question Generation <span class="new-badge">NEW</span><br>
                Enhanced AI Scoring <span class="new-badge">NEW</span><br>
                Performance Analytics <span class="new-badge">NEW</span><br>
                Mobile-Responsive Design <span class="new-badge">NEW</span>
            </div>
        </div>
    </div>
</body>
</html>""")

@app.route('/logout')
def logout():
    user_id = session.get('user_id')
    if user_id:
        DatabaseManager.log_analytics('logout', user_id)
    
    session.clear()
    return redirect('/login')

@app.route('/admin')
def admin():
    if not session.get('is_admin'):
        return redirect('/login')
    
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    # Get comprehensive statistics
    c.execute('SELECT COUNT(*) FROM users WHERE is_admin = 0')
    total_engineers = c.fetchone()[0]
    
    c.execute('SELECT COUNT(*) FROM assignments')
    total_assignments = c.fetchone()[0]
    
    c.execute('SELECT COUNT(*) FROM submissions WHERE status = "submitted"')
    pending_reviews = c.fetchone()[0]
    
    c.execute('SELECT COUNT(*) FROM submissions WHERE status = "graded"')
    completed_reviews = c.fetchone()[0]
    
    # Get engineers for dropdown
    c.execute('SELECT * FROM users WHERE is_admin = 0 ORDER BY display_name')
    engineers = c.fetchall()
    
    # Get recent activity
    c.execute('''
        SELECT s.*, a.topic, u.display_name, a.created_date as assignment_date
        FROM submissions s
        JOIN assignments a ON s.assignment_id = a.id
        JOIN users u ON s.engineer_id = u.id
        WHERE s.status = "submitted"
        ORDER BY s.submitted_date DESC
        LIMIT 10
    ''')
    pending_submissions = c.fetchall()
    
    # Get performance analytics
    c.execute('''
        SELECT 
            topic,
            COUNT(*) as count,
            AVG(CAST(total_score as FLOAT)) as avg_score,
            MAX(CAST(total_score as FLOAT)) as max_score,
            MIN(CAST(total_score as FLOAT)) as min_score
        FROM submissions s
        JOIN assignments a ON s.assignment_id = a.id
        WHERE s.status = "graded" AND s.total_score > 0
        GROUP BY topic
    ''')
    topic_stats = c.fetchall()
    
    conn.close()
    
    # Build engineer options
    eng_options = ''
    for eng in engineers:
        exp_years = eng[6] if eng[6] else 3
        eng_options += f'<option value="{eng[0]}" data-exp="{exp_years}">{eng[2]} ({exp_years}y exp)</option>'
    
    # Build pending submissions HTML
    pending_html = ''
    for sub in pending_submissions:
        time_ago = _time_ago(sub[4])
        pending_html += f'''
        <div class="submission-card">
            <div class="submission-header">
                <h4>{sub[11]} - {sub[10].upper()}</h4>
                <span class="time-badge">{time_ago}</span>
            </div>
            <div class="submission-meta">
                📝 {len(json.loads(sub[3]))} answers | 🎯 Auto-scored | ⏰ {sub[4][:16]}
            </div>
            <div class="submission-actions">
                <a href="/admin/review/{sub[1]}" class="review-btn">Review & Grade</a>
            </div>
        </div>'''
    
    if not pending_html:
        pending_html = '''
        <div class="no-submissions">
            <div class="empty-icon">📭</div>
            <h3>All Caught Up!</h3>
            <p>No pending submissions to review. Great work!</p>
        </div>'''
    
    # Build analytics charts data
    analytics_data = {
        "topic_stats": [{"topic": stat[0], "count": stat[1], "avg_score": round(stat[2], 1)} for stat in topic_stats],
        "total_engineers": total_engineers,
        "completion_rate": round((completed_reviews / max(total_assignments, 1)) * 100, 1)
    }
    
    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
    <title>Enhanced Admin Dashboard - Vibhuayu</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        :root {
            --primary: #667eea;
            --secondary: #764ba2;
            --success: #10b981;
            --warning: #f59e0b;
            --error: #ef4444;
            --bg-dark: #0f172a;
            --bg-light: #1e293b;
            --surface: #ffffff;
            --text-primary: #1e293b;
            --text-secondary: #64748b;
            --border: #e2e8f0;
        }
        
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, var(--bg-dark) 0%, var(--bg-light) 100%);
            min-height: 100vh; color: var(--text-primary);
        }
        
        .header {
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            padding: 20px 0; box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
            position: relative; overflow: hidden;
        }
        
        .header::before {
            content: ''; position: absolute;
            top: 0; left: 0; right: 0; bottom: 0;
            background: linear-gradient(45deg, transparent 30%, rgba(255,255,255,0.1) 50%, transparent 70%);
            transform: translateX(-100%);
            animation: headerShine 4s infinite;
        }
        
        @keyframes headerShine {
            0% { transform: translateX(-100%); }
            50% { transform: translateX(100%); }
            100% { transform: translateX(100%); }
        }
        
        .header-content {
            max-width: 1400px; margin: 0 auto; padding: 0 20px;
            display: flex; align-items: center; justify-content: space-between;
            position: relative; z-index: 2;
        }
        
        .header-title {
            display: flex; align-items: center; gap: 15px;
        }
        
        .header-logo {
            width: 50px; height: 50px;
            background: rgba(255, 255, 255, 0.15);
            border-radius: 12px; display: flex; align-items: center; justify-content: center;
            font-weight: 900; color: white; font-size: 20px;
            backdrop-filter: blur(10px);
        }
        
        .header h1 {
            color: white; font-size: 28px; font-weight: 700;
            text-shadow: 0 2px 10px rgba(0,0,0,0.3);
        }
        
        .nav-menu {
            display: flex; gap: 15px; align-items: center;
        }
        
        .nav-btn {
            background: rgba(255, 255, 255, 0.15); color: white;
            padding: 10px 15px; text-decoration: none; border-radius: 8px;
            backdrop-filter: blur(10px); transition: all 0.3s ease;
            font-weight: 600; font-size: 14px;
        }
        
        .nav-btn:hover {
            background: rgba(255, 255, 255, 0.25);
            transform: translateY(-2px);
        }
        
        .container {
            max-width: 1400px; margin: 30px auto; padding: 0 20px;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 25px; margin-bottom: 40px;
        }
        
        .stat-card {
            background: linear-gradient(135deg, var(--surface) 0%, #f8fafc 100%);
            padding: 30px; border-radius: 20px; text-align: center;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.2);
            transition: transform 0.3s ease;
        }
        
        .stat-card:hover { transform: translateY(-5px); }
        
        .stat-number {
            font-size: 42px; font-weight: 800;
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            margin-bottom: 8px; line-height: 1;
        }
        
        .stat-label {
            color: var(--text-secondary); font-weight: 600;
            font-size: 14px; text-transform: uppercase; letter-spacing: 1px;
        }
        
        .stat-trend {
            margin-top: 10px; font-size: 12px; font-weight: 600;
        }
        
        .trend-up { color: var(--success); }
        .trend-down { color: var(--error); }
        
        .main-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
        }
        
        .card {
            background: linear-gradient(135deg, var(--surface) 0%, #f8fafc 100%);
            border-radius: 20px; padding: 30px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.2);
        }
        
        .card h2 {
            color: var(--text-primary); margin-bottom: 25px;
            font-size: 24px; font-weight: 700;
            display: flex; align-items: center; gap: 10px;
        }
        
        .form-row {
            display: grid;
            grid-template-columns: 1fr 1fr auto;
            gap: 15px; align-items: end;
        }
        
        .form-group {
            display: flex; flex-direction: column;
        }
        
        .form-group label {
            margin-bottom: 8px; font-weight: 600;
            color: var(--text-primary); font-size: 14px;
        }
        
        select, button {
            padding: 14px 18px; border: 2px solid var(--border);
            border-radius: 12px; font-size: 16px;
            transition: all 0.3s ease; background: white;
            font-family: inherit;
        }
        
        select:focus {
            outline: none; border-color: var(--primary);
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }
        
        .btn-primary {
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            color: white; border: none; cursor: pointer;
            font-weight: 600; min-width: 140px;
        }
        
        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 25px rgba(102, 126, 234, 0.4);
        }
        
        .submission-card {
            background: linear-gradient(135deg, #f8fafc, #f1f5f9);
            padding: 20px; margin: 15px 0; border-radius: 16px;
            border-left: 4px solid var(--warning);
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.05);
            transition: all 0.3s ease;
        }
        
        .submission-card:hover {
            transform: translateX(5px);
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);
        }
        
        .submission-header {
            display: flex; justify-content: space-between;
            align-items: center; margin-bottom: 10px;
        }
        
        .submission-header h4 {
            color: var(--text-primary); margin: 0; font-size: 16px;
        }
        
        .time-badge {
            background: var(--warning); color: white;
            padding: 4px 12px; border-radius: 20px;
            font-size: 12px; font-weight: 600;
        }
        
        .submission-meta {
            color: var(--text-secondary); font-size: 14px;
            margin-bottom: 15px;
        }
        
        .submission-actions {
            display: flex; gap: 10px;
        }
        
        .review-btn {
            padding: 8px 16px; text-decoration: none;
            border-radius: 8px; font-weight: 600;
            font-size: 14px; transition: all 0.3s ease;
            background: linear-gradient(135deg, var(--success), #059669);
            color: white;
        }
        
        .review-btn:hover {
            transform: translateY(-2px);
        }
        
        .no-submissions {
            text-align: center; padding: 60px 20px;
            color: var(--text-secondary);
        }
        
        .empty-icon {
            font-size: 48px; margin-bottom: 20px;
        }
        
        .analytics-preview {
            background: linear-gradient(135deg, #f0f9ff, #e0f2fe);
            border-radius: 12px; padding: 20px;
            margin-top: 20px;
        }
        
        .analytics-item {
            display: flex; justify-content: space-between;
            align-items: center; padding: 10px 0;
            border-bottom: 1px solid rgba(102, 126, 234, 0.1);
        }
        
        .analytics-item:last-child { border-bottom: none; }
        
        @media (max-width: 768px) {
            .main-grid { grid-template-columns: 1fr; }
            .form-row { grid-template-columns: 1fr; gap: 15px; }
            .stats-grid { grid-template-columns: repeat(2, 1fr); }
            .header-content { flex-direction: column; gap: 15px; text-align: center; }
            .nav-menu { flex-wrap: wrap; justify-content: center; }
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="header-content">
            <div class="header-title">
                <div class="header-logo">V7</div>
                <h1>🚀 Enhanced Admin Dashboard</h1>
            </div>
            <div class="nav-menu">
                <a href="/admin/analytics" class="nav-btn">📊 Analytics</a>
                <a href="/logout" class="nav-btn">🚪 Logout</a>
            </div>
        </div>
    </div>
    
    <div class="container">
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-number">{{ total_engineers }}</div>
                <div class="stat-label">Engineers</div>
                <div class="stat-trend trend-up">↗ Active Users</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ total_assignments }}</div>
                <div class="stat-label">Assessments</div>
                <div class="stat-trend trend-up">📈 Total Created</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ pending_reviews }}</div>
                <div class="stat-label">Pending Reviews</div>
                <div class="stat-trend trend-up">⏳ Need Attention</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ analytics_data.completion_rate }}%</div>
                <div class="stat-label">Completion Rate</div>
                <div class="stat-trend trend-up">✅ Success Rate</div>
            </div>
        </div>
        
        <div class="main-grid">
            <div class="card">
                <h2>🎯 Create Smart Assessment</h2>
                <form method="POST" action="/admin/create">
                    <div class="form-row">
                        <div class="form-group">
                            <label>Select Engineer</label>
                            <select name="engineer_id" required id="engineerSelect">
                                <option value="">Choose engineer...</option>
                                {{ eng_options }}
                            </select>
                        </div>
                        <div class="form-group">
                            <label>Assessment Topic</label>
                            <select name="topic" required>
                                <option value="">Select topic...</option>
                                <option value="sta">🕒 STA (Static Timing Analysis)</option>
                                <option value="cts">🌳 CTS (Clock Tree Synthesis)</option>
                                <option value="signoff">✅ Signoff Checks & Verification</option>
                            </select>
                        </div>
                        <button type="submit" class="btn-primary">Create Assessment</button>
                    </div>
                    <div class="analytics-preview">
                        <div class="analytics-item">
                            <span>📝 Questions Generated:</span>
                            <strong>18 (Adaptive Difficulty)</strong>
                        </div>
                        <div class="analytics-item">
                            <span>🤖 AI Scoring:</span>
                            <strong>Enabled</strong>
                        </div>
                        <div class="analytics-item">
                            <span>📊 Analytics Tracking:</span>
                            <strong>Full Coverage</strong>
                        </div>
                    </div>
                </form>
            </div>
            
            <div class="card">
                <h2>📋 Pending Reviews ({{ pending_reviews }})</h2>
                <div style="max-height: 400px; overflow-y: auto;">
                    {{ pending_html|safe }}
                </div>
            </div>
        </div>
        
        {% if analytics_data.topic_stats %}
        <div class="card" style="margin-top: 30px;">
            <h2>📈 Performance Analytics</h2>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px;">
                {% for stat in analytics_data.topic_stats %}
                <div class="analytics-item">
                    <div>
                        <span style="background: var(--primary); color: white; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; text-transform: uppercase;">{{ stat.topic }}</span>
                        <div style="margin-top: 8px;">
                            <strong>{{ stat.count }}</strong> submissions<br>
                            <strong>{{ stat.avg_score }}</strong> avg score
                        </div>
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>
        {% endif %}
    </div>
    
    <script>
        // Enhanced interactivity
        document.getElementById('engineerSelect').addEventListener('change', function() {
            const selectedOption = this.selectedOptions[0];
            const experience = selectedOption.getAttribute('data-exp');
            if (experience) {
                console.log(`Selected engineer with ${experience} years experience`);
            }
        });
        
        // Auto-refresh pending count every 30 seconds
        setInterval(() => {
            fetch('/admin/stats')
                .then(response => response.json())
                .then(data => {
                    console.log('Stats updated');
                })
                .catch(err => console.log('Stats update failed'));
        }, 30000);
    </script>
</body>
</html>""", 
    total_engineers=total_engineers,
    total_assignments=total_assignments,
    pending_reviews=pending_reviews,
    completed_reviews=completed_reviews,
    eng_options=eng_options,
    pending_html=pending_html,
    analytics_data=analytics_data
    )

@app.route('/admin/create', methods=['POST'])
def admin_create():
    if not session.get('is_admin'):
        return redirect('/login')
    
    engineer_id = request.form.get('engineer_id')
    topic = request.form.get('topic')
    
    if not engineer_id or not topic:
        return redirect('/admin')
    
    # Get engineer experience for adaptive questions
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('SELECT experience FROM users WHERE id = ?', (engineer_id,))
    engineer = c.fetchone()
    experience = engineer[0] if engineer else 3
    
    # Generate smart questions
    questions = question_generator.generate_smart_questions(topic, 18, experience)
    
    # Create assignment
    assignment_id = f"PD_{topic}_{engineer_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    due_date = (datetime.now() + timedelta(days=7)).isoformat()
    
    c.execute("""
        INSERT INTO assignments (id, engineer_id, topic, questions, created_date, due_date, created_by)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (assignment_id, engineer_id, topic, json.dumps(questions), 
          datetime.now().isoformat(), due_date, session['user_id']))
    
    conn.commit()
    conn.close()
    
    # Log analytics
    DatabaseManager.log_analytics('assignment_created', session['user_id'], {
        'assignment_id': assignment_id,
        'topic': topic,
        'engineer_id': engineer_id
    })
    
    return redirect('/admin')

@app.route('/admin/review/<assignment_id>', methods=['GET', 'POST'])
def admin_review(assignment_id):
    if not session.get('is_admin'):
        return redirect('/login')
    
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    # Get submission details
    c.execute('''
        SELECT s.*, a.topic, a.questions, u.display_name
        FROM submissions s
        JOIN assignments a ON s.assignment_id = a.id
        JOIN users u ON s.engineer_id = u.id
        WHERE s.assignment_id = ?
    ''', (assignment_id,))
    submission = c.fetchone()
    
    if not submission:
        conn.close()
        return redirect('/admin')
    
    # Process submission data
    answers = json.loads(submission[3])
    questions = json.loads(submission[12])
    auto_scores = json.loads(submission[6]) if submission[6] else {}
    
    # Handle grading submission
    if request.method == 'POST':
        manual_scores = {}
        feedback_notes = {}
        total_score = 0
        
        for i in range(len(questions)):
            manual_score = request.form.get(f'score_{i}', 0)
            feedback_note = request.form.get(f'feedback_{i}', '')
            try:
                score = float(manual_score)
                manual_scores[str(i)] = score
                feedback_notes[str(i)] = feedback_note
                total_score += score
            except:
                manual_scores[str(i)] = 0
        
        # Update submission with grades
        c.execute('''
            UPDATE submissions 
            SET manual_scores = ?, feedback = ?, total_score = ?, 
                status = 'graded', graded_by = ?, graded_date = ?
            WHERE assignment_id = ?
        ''', (json.dumps(manual_scores), json.dumps(feedback_notes), 
              total_score, session['user_id'], datetime.now().isoformat(), assignment_id))
        conn.commit()
        conn.close()
        
        # Log analytics
        DatabaseManager.log_analytics('submission_graded', session['user_id'], {
            'assignment_id': assignment_id,
            'total_score': total_score,
            'engineer_id': submission[2]
        })
        
        return redirect('/admin')
    
    conn.close()
    
    # Build review interface
    questions_html = ''
    for i, question in enumerate(questions):
        answer = answers.get(str(i), 'No answer provided')
        auto_score_data = auto_scores.get(str(i), {})
        suggested_score = auto_score_data.get('score', 0)
        
        # Enhanced scoring analysis
        if answer and answer != 'No answer provided':
            score_analysis = scoring_system.analyze_answer_comprehensive(question, answer, submission[11])
            suggested_score = score_analysis['score']
            breakdown = score_analysis['breakdown']
            suggestions = score_analysis['suggestions']
        else:
            breakdown = {"technical": 0, "depth": 0, "methodology": 0, "clarity": 0}
            suggestions = ["Answer not provided"]
        
        color = "#10b981" if suggested_score >= 7 else "#f59e0b# Enhanced PD Assessment System - Complete app.py for Railway
import os
import hashlib
import json
import random
import sqlite3
from datetime import datetime, timedelta
from threading import Lock
from flask import Flask, request, redirect, session, jsonify, render_template_string
import re

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'pd-secret-key-enhanced')

# Database setup
DATABASE = 'enhanced_assessments.db'
db_lock = Lock()

class DatabaseManager:
    @staticmethod
    def init_db():
        """Initialize SQLite database with enhanced schema"""
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        
        # Users table
        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE,
                display_name TEXT,
                email TEXT,
                password TEXT,
                is_admin BOOLEAN DEFAULT 0,
                experience INTEGER DEFAULT 3,
                department TEXT,
                created_date TEXT,
                last_login TEXT,
                theme TEXT DEFAULT 'light'
            )
        """)
        
        # Assignments table
        c.execute("""
            CREATE TABLE IF NOT EXISTS assignments (
                id TEXT PRIMARY KEY,
                engineer_id TEXT,
                topic TEXT,
                questions TEXT,
                created_date TEXT,
                due_date TEXT,
                status TEXT DEFAULT 'pending',
                difficulty_level INTEGER DEFAULT 1,
                max_points INTEGER DEFAULT 180,
                created_by TEXT,
                FOREIGN KEY (engineer_id) REFERENCES users (id)
            )
        """)
        
        # Submissions table (enhanced)
        c.execute("""
            CREATE TABLE IF NOT EXISTS submissions (
                id TEXT PRIMARY KEY,
                assignment_id TEXT,
                engineer_id TEXT,
                answers TEXT,
                submitted_date TEXT,
                status TEXT DEFAULT 'submitted',
                auto_scores TEXT,
                manual_scores TEXT,
                feedback TEXT,
                total_score INTEGER DEFAULT 0,
                graded_by TEXT,
                graded_date TEXT,
                time_spent INTEGER DEFAULT 0,
                FOREIGN KEY (assignment_id) REFERENCES assignments (id),
                FOREIGN KEY (engineer_id) REFERENCES users (id)
            )
        """)
        
        # Analytics table
        c.execute("""
            CREATE TABLE IF NOT EXISTS analytics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT,
                user_id TEXT,
                data TEXT,
                timestamp TEXT
            )
        """)
        
        conn.commit()
        conn.close()
    
    @staticmethod
    def log_analytics(event_type, user_id, data=None):
        """Log analytics events"""
        with db_lock:
            conn = sqlite3.connect(DATABASE)
            c = conn.cursor()
            c.execute("""
                INSERT INTO analytics (event_type, user_id, data, timestamp)
                VALUES (?, ?, ?, ?)
            """, (event_type, user_id, json.dumps(data) if data else None, datetime.now().isoformat()))
            conn.commit()
            conn.close()

# Enhanced Question Generation with Smart AI
class SmartQuestionGenerator:
    def __init__(self):
        self.question_templates = {
            "sta": [
                {
                    "template": "Your design has {violation_type} violations of {violation_amount}ps on {num_paths} critical paths. The design is running at {frequency}MHz. Analyze the root causes and propose {num_solutions} specific solutions with expected improvement estimates.",
                    "difficulty": 3,
                    "parameters": {
                        "violation_type": ["setup", "hold", "max_transition"],
                        "violation_amount": [20, 50, 100, 150, 200],
                        "num_paths": [10, 25, 50, 100, 200],
                        "frequency": [500, 800, 1000, 1500, 2000],
                        "num_solutions": [3, 4, 5]
                    }
                },
                {
                    "template": "Explain the concept of {concept} in static timing analysis. How does it impact {impact_area} and what are the industry-standard approaches to handle it in {technology_node} designs?",
                    "difficulty": 2,
                    "parameters": {
                        "concept": ["clock jitter", "OCV", "useful skew", "clock latency", "timing corners"],
                        "impact_area": ["setup timing", "hold timing", "power consumption", "area optimization"],
                        "technology_node": ["7nm", "5nm", "3nm", "advanced nodes"]
                    }
                },
                {
                    "template": "You're analyzing a {design_type} with {num_domains} clock domains running at different frequencies. Describe your approach to handle clock domain crossings and ensure timing closure across all interfaces.",
                    "difficulty": 4,
                    "parameters": {
                        "design_type": ["SoC", "CPU", "GPU", "AI accelerator"],
                        "num_domains": [3, 4, 5, 6]
                    }
                }
            ],
            "cts": [
                {
                    "template": "Design a clock tree for a {design_size} design with {num_flops} flip-flops distributed across {die_size}. The target skew is {target_skew}ps and you have {buffer_types} buffer types available. Explain your tree topology choice and optimization strategy.",
                    "difficulty": 3,
                    "parameters": {
                        "design_size": ["large-scale", "medium-scale", "complex"],
                        "num_flops": [10000, 25000, 50000, 100000],
                        "die_size": ["5mm x 5mm", "10mm x 10mm", "15mm x 15mm"],
                        "target_skew": [25, 50, 75, 100],
                        "buffer_types": [3, 4, 5, 6]
                    }
                },
                {
                    "template": "Your clock tree has {power_consumption}mW power consumption, which is {percentage}% of total chip power. Propose {num_techniques} specific techniques to reduce clock power while maintaining {skew_constraint}ps skew constraint.",
                    "difficulty": 4,
                    "parameters": {
                        "power_consumption": [50, 100, 150, 200],
                        "percentage": [15, 20, 25, 30, 35],
                        "num_techniques": [3, 4, 5],
                        "skew_constraint": [30, 50, 75]
                    }
                }
            ],
            "signoff": [
                {
                    "template": "Your design failed {check_type} with {num_violations} violations. The violations are distributed as: {violation_dist}. Create a systematic debugging and resolution plan with priority ordering and estimated effort.",
                    "difficulty": 3,
                    "parameters": {
                        "check_type": ["DRC", "LVS", "Antenna", "Metal Density"],
                        "num_violations": [50, 100, 200, 500],
                        "violation_dist": ["70% spacing, 20% width, 10% via", "50% density, 30% spacing, 20% antenna"]
                    }
                },
                {
                    "template": "Perform signoff analysis for a {design_type} in {technology} process. The design has {power_domains} power domains and {io_count} I/Os. List all required signoff checks and create a verification plan with timeline.",
                    "difficulty": 4,
                    "parameters": {
                        "design_type": ["automotive SoC", "mobile processor", "IoT chip", "high-performance CPU"],
                        "technology": ["7nm FinFET", "5nm", "3nm GAA"],
                        "power_domains": [2, 3, 4, 5],
                        "io_count": [100, 200, 500, 1000]
                    }
                }
            ]
        }
    
    def generate_smart_questions(self, topic, num_questions=18, engineer_exp=3):
        """Generate questions with adaptive difficulty"""
        templates = self.question_templates.get(topic, [])
        if not templates:
            return self._fallback_questions(topic)
        
        questions = []
        difficulty_distribution = self._get_difficulty_distribution(engineer_exp, num_questions)
        
        for target_difficulty in difficulty_distribution:
            suitable_templates = [t for t in templates if abs(t["difficulty"] - target_difficulty) <= 1]
            if not suitable_templates:
                suitable_templates = templates
            
            template = random.choice(suitable_templates)
            question = self._generate_from_template(template)
            questions.append(question)
        
        return questions[:num_questions]
    
    def _get_difficulty_distribution(self, engineer_exp, num_questions):
        """Create difficulty distribution based on experience"""
        if engineer_exp <= 2:
            easy_count = int(num_questions * 0.6)
            medium_count = int(num_questions * 0.3)
            hard_count = num_questions - easy_count - medium_count
            return [2] * easy_count + [3] * medium_count + [4] * hard_count
        elif engineer_exp <= 4:
            easy_count = int(num_questions * 0.3)
            medium_count = int(num_questions * 0.5)
            hard_count = num_questions - easy_count - medium_count
            return [2] * easy_count + [3] * medium_count + [4] * hard_count
        else:
            easy_count = int(num_questions * 0.2)
            medium_count = int(num_questions * 0.4)
            hard_count = num_questions - easy_count - medium_count
            return [2] * easy_count + [3] * medium_count + [4] * hard_count
    
    def _generate_from_template(self, template_data):
        """Generate question from template with random parameters"""
        template = template_data["template"]
        params = template_data["parameters"]
        
        generated_params = {}
        for param, options in params.items():
            generated_params[param] = random.choice(options)
        
        try:
            return template.format(**generated_params)
        except KeyError:
            return template
    
    def _fallback_questions(self, topic):
        """Fallback to static questions if smart generation fails"""
        fallback = {
            "sta": [
                "What is Static Timing Analysis and why is it critical in modern chip design?",
                "Explain setup and hold time violations. How do you debug and fix them?",
                "What is clock skew and how does it impact timing closure?",
                "Describe the concept of timing corners and their importance in analysis.",
                "How do you handle timing analysis for multiple clock domains?",
                "What are timing exceptions and when would you use false paths?",
                "Explain the difference between ideal clock and propagated clock analysis.",
                "What is clock jitter and how do you account for it in timing calculations?",
                "How do you analyze timing for memory interfaces and what makes them special?",
                "What is OCV (On-Chip Variation) and why do you add OCV margins in STA?",
                "Explain multicycle paths and give an example where you would use them.",
                "How do you handle timing analysis for generated clocks and clock dividers?",
                "What is clock domain crossing (CDC) and what timing checks are needed?",
                "Describe timing analysis for high-speed interfaces and their challenges.",
                "What reports do you check for timing signoff and why are they important?",
                "How do you ensure timing correlation between STA tools and silicon?",
                "What is useful skew and how can it help with timing closure?",
                "Explain timing optimization techniques for low-power designs."
            ],
            "cts": [
                "What is Clock Tree Synthesis and what are its main objectives?",
                "Explain different clock tree topologies and when to use each.",
                "How do you optimize clock trees for power consumption?",
                "What is useful skew and how can it help timing closure?",
                "Describe challenges in CTS for high-frequency designs.",
                "What is clock skew and what causes it in clock trees?",
                "How do you handle clock gating cells in clock tree synthesis?",
                "Explain the concept of clock insertion delay and how to minimize it.",
                "What are the trade-offs between H-tree and balanced tree topologies?",
                "How do you handle multiple clock domains in CTS?",
                "What is clock mesh and when would you choose it over tree topology?",
                "Describe clock tree optimization for process variation and yield.",
                "How do you build clock trees for multi-voltage designs?",
                "What is the typical CTS flow and when does it happen in the design cycle?",
                "How do you verify clock tree quality after synthesis?",
                "What are the challenges of clock tree synthesis in advanced nodes?",
                "Explain clock tree balancing and why it's important.",
                "How do you handle clock tree synthesis for low-power designs?"
            ],
            "signoff": [
                "What are the main signoff checks required before tape-out?",
                "Explain DRC violations and systematic approaches to fix them.",
                "What is LVS and how do you debug LVS mismatches?",
                "Describe IR drop analysis and mitigation techniques.",
                "How do you perform timing signoff for multi-corner analysis?",
                "What is antenna checking and why can violations damage your chip?",
                "Explain metal density rules and their impact on manufacturing.",
                "What is electromigration and how do you prevent EM violations?",
                "How do you perform signal integrity analysis during signoff?",
                "What is formal verification and how does it differ from simulation?",
                "Describe the signoff flow for advanced technology nodes.",
                "How do you coordinate signoff across different design teams?",
                "What additional checks are needed for multi-voltage designs?",
                "Explain thermal analysis and its importance in signoff.",
                "What is yield analysis and how do you optimize for manufacturing yield?",
                "How do you validate power delivery networks during signoff?",
                "What are the challenges of signoff in 7nm and below technologies?",
                "Describe the handoff process between design and manufacturing teams."
            ]
        }
        
        base_questions = fallback.get(topic, fallback["sta"])
        extended = []
        for i in range(18):
            base_q = base_questions[i % len(base_questions)]
            if i >= len(base_questions):
                extended.append(f"Advanced: {base_q}")
            else:
                extended.append(base_q)
        return extended

# Enhanced Scoring System
class EnhancedScoringSystem:
    def __init__(self):
        self.scoring_rubrics = {
            "sta": {
                "technical_terms": ["setup", "hold", "slack", "skew", "jitter", "corner", "violation", "closure"],
                "advanced_terms": ["ocv", "cppr", "useful skew", "clock latency", "propagated", "ideal"],
                "methodology_terms": ["debug", "optimize", "analyze", "systematic", "root cause"],
                "weights": {"technical": 0.4, "depth": 0.3, "methodology": 0.2, "clarity": 0.1}
            },
            "cts": {
                "technical_terms": ["clock tree", "skew", "insertion delay", "buffer", "topology", "synthesis"],
                "advanced_terms": ["h-tree", "mesh", "useful skew", "gating", "power optimization"],
                "methodology_terms": ["balance", "optimize", "strategy", "approach", "technique"],
                "weights": {"technical": 0.4, "depth": 0.3, "methodology": 0.2, "clarity": 0.1}
            },
            "signoff": {
                "technical_terms": ["drc", "lvs", "antenna", "density", "ir drop", "em", "signoff"],
                "advanced_terms": ["formal verification", "multi-corner", "yield analysis", "si analysis"],
                "methodology_terms": ["debug", "systematic", "flow", "process", "validation"],
                "weights": {"technical": 0.4, "depth": 0.3, "methodology": 0.2, "clarity": 0.1}
            }
        }
    
    def analyze_answer_comprehensive(self, question, answer, topic):
        """Comprehensive answer analysis with detailed feedback"""
        if not answer or len(answer.strip()) < 20:
            return {
                "score": 0,
                "breakdown": {"technical": 0, "depth": 0, "methodology": 0, "clarity": 0},
                "feedback": "Answer too short or empty",
                "suggestions": ["Provide more detailed technical explanation", "Include specific examples", "Explain methodology"]
            }
        
        rubric = self.scoring_rubrics.get(topic, self.scoring_rubrics["sta"])
        answer_lower = answer.lower()
        word_count = len(answer.split())
        
        # Technical accuracy score
        technical_score = self._score_technical_content(answer_lower, rubric)
        
        # Depth and detail score
        depth_score = self._score_depth(answer, word_count)
        
        # Methodology score
        methodology_score = self._score_methodology(answer_lower, rubric)
        
        # Clarity and structure score
        clarity_score = self._score_clarity(answer)
        
        # Weighted final score
        weights = rubric["weights"]
        final_score = (
            technical_score * weights["technical"] +
            depth_score * weights["depth"] +
            methodology_score * weights["methodology"] +
            clarity_score * weights["clarity"]
        ) * 10
        
        # Generate feedback and suggestions
        feedback, suggestions = self._generate_feedback(
            technical_score, depth_score, methodology_score, clarity_score, word_count
        )
        
        return {
            "score": round(final_score, 1),
            "breakdown": {
                "technical": round(technical_score * 10, 1),
                "depth": round(depth_score * 10, 1),
                "methodology": round(methodology_score * 10, 1),
                "clarity": round(clarity_score * 10, 1)
            },
            "feedback": feedback,
            "suggestions": suggestions,
            "word_count": word_count
        }
    
    def _score_technical_content(self, answer_lower, rubric):
        tech_terms = sum(1 for term in rubric["technical_terms"] if term in answer_lower)
        advanced_terms = sum(1 for term in rubric["advanced_terms"] if term in answer_lower)
        
        tech_score = min(tech_terms / 3, 1.0)
        advanced_score = min(advanced_terms / 2, 0.5)
        
        return min(tech_score + advanced_score, 1.0)
    
    def _score_depth(self, answer, word_count):
        word_score = min(word_count / 100, 0.7)
        
        has_examples = any(marker in answer.lower() for marker in ['example', 'for instance', 'such as'])
        has_numbers = bool(re.search(r'\d+', answer))
        has_comparisons = any(marker in answer.lower() for marker in ['compare', 'versus', 'vs', 'better', 'worse'])
        
        structure_score = (has_examples * 0.1) + (has_numbers * 0.1) + (has_comparisons * 0.1)
        
        return min(word_score + structure_score, 1.0)
    
    def _score_methodology(self, answer_lower, rubric):
        method_terms = sum(1 for term in rubric["methodology_terms"] if term in answer_lower)
        
        has_steps = any(marker in answer_lower for marker in ['step', 'first', 'second', 'then', 'next', 'finally'])
        has_process = any(marker in answer_lower for marker in ['process', 'flow', 'procedure', 'approach'])
        
        method_score = min(method_terms / 2, 0.7)
        process_score = (has_steps * 0.15) + (has_process * 0.15)
        
        return min(method_score + process_score, 1.0)
    
    def _score_clarity(self, answer):
        sentences = answer.split('.')
        avg_sentence_length = sum(len(s.split()) for s in sentences) / max(len(sentences), 1)
        
        length_score = 1.0 - abs(avg_sentence_length - 17.5) / 17.5
        length_score = max(0, min(length_score, 1.0))
        
        has_organization = any(marker in answer.lower() for marker in [':', '-', '1.', '2.', 'bullet'])
        org_score = 0.3 if has_organization else 0
        
        return min(length_score * 0.7 + org_score, 1.0)
    
    def _generate_feedback(self, tech_score, depth_score, method_score, clarity_score, word_count):
        feedback_parts = []
        suggestions = []
        
        if tech_score >= 0.8:
            feedback_parts.append("Strong technical knowledge demonstrated")
        elif tech_score >= 0.6:
            feedback_parts.append("Good technical understanding shown")
            suggestions.append("Include more specific technical terminology")
        else:
            feedback_parts.append("Limited technical content")
            suggestions.append("Use more industry-specific technical terms")
        
        if depth_score >= 0.8:
            feedback_parts.append("comprehensive analysis provided")
        elif depth_score >= 0.6:
            feedback_parts.append("adequate detail level")
            suggestions.append("Provide more detailed explanations and examples")
        else:
            feedback_parts.append("needs more depth")
            suggestions.append("Expand with specific examples and quantitative details")
        
        if method_score >= 0.7:
            feedback_parts.append("clear methodology described")
        else:
            feedback_parts.append("methodology could be clearer")
            suggestions.append("Describe step-by-step approach or process")
        
        if word_count < 50:
            suggestions.append("Increase answer length for better coverage")
        elif word_count > 300:
            suggestions.append("Consider more concise explanations")
        
        feedback = ", ".join(feedback_parts).capitalize() + f" ({word_count} words)"
        
        return feedback, suggestions

# Initialize components
DatabaseManager.init_db()
question_generator = SmartQuestionGenerator()
scoring_system = EnhancedScoringSystem()

# User authentication functions
def hash_pass(pwd):
    return hashlib.sha256(pwd.encode()).hexdigest()

def check_pass(hashed, pwd):
    return hashed == hashlib.sha256(pwd.encode()).hexdigest()

def init_data():
    """Initialize demo data"""
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    # Check if admin exists
    c.execute('SELECT id FROM users WHERE id = ?', ('admin',))
    if not c.fetchone():
        # Create admin
        c.execute("""
            INSERT INTO users (id, username, display_name, email, password, is_admin, experience, created_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, ('admin', 'admin', 'System Administrator', 'admin@vibhuayu.com', 
              hash_pass('Vibhuaya@3006'), 1, 5, datetime.now().isoformat()))
        
        # Create 18 engineers
        engineer_data = [
            ('eng001', 'Kranthi', 'kranthi@vibhuayu.com', 3),
            ('eng002', 'Neela', 'neela@vibhuayu.com', 4),
            ('eng003', 'Bhanu', 'bhanu@vibhuayu.com', 2),
            ('eng004', 'Lokeshwari', 'lokeshwari@vibhuayu.com', 5),
            ('eng005', 'Nagesh', 'nagesh@vibhuayu.com', 3),
            ('eng006', 'VJ', 'vj@vibhuayu.com', 4),
            ('eng007', 'Pravalika', 'pravalika@vibhuayu.com', 2),
            ('eng008', 'Daniel', 'daniel@vibhuayu.com', 6),
            ('eng009', 'Karthik', 'karthik@vibhuayu.com', 3),
            ('eng010', 'Hema', 'hema@vibhuayu.com', 4),
            ('eng011', 'Naveen', 'naveen@vibhuayu.com', 5),
            ('eng012', 'Srinivas', 'srinivas@vibhuayu.com', 3),
            ('eng013', 'Meera', 'meera@vibhuayu.com', 2),
            ('eng014', 'Suraj', 'suraj@vibhuayu.com', 4),
            ('eng015', 'Akhil', 'akhil@vibhuayu.com', 3),
            ('eng016', 'Vikas', 'vikas@vibhuayu.com', 5),
            ('eng017', 'Sahith', 'sahith@vibhuayu.com', 2),
            ('eng018', 'Sravan', 'sravan@vibhuayu.com', 4)
        ]
        
        for uid, name, email, exp in engineer_data:
            c.execute("""
                INSERT INTO users (id, username, display_name, email, password, is_admin, experience, department, created_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (uid, uid, name, email, hash_pass('password123'), 0, exp, 'Physical Design', datetime.now().isoformat()))
    
    conn.commit()
    conn.close()

def _time_ago(date_str):
    """Calculate time ago from date string"""
    try:
        date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        now = datetime.now()
        diff = now - date_obj
        
        if diff.days > 0:
            return f"{diff.days}d ago"
        elif diff.seconds > 3600:
            return f"{diff.seconds // 3600}h ago"
        elif diff.seconds > 60:
            return f"{diff.seconds // 60}m ago"
        else:
            return "Just now"
    except:
        return "Unknown"

# Routes
@app.route('/')
def home():
    if 'user_id' in session:
        if session.get('is_admin'):
            return redirect('/admin')
        return redirect('/student')
    return redirect('/login')

@app.route('/health')
def health():
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE username = ?', (username,))
        user = c.fetchone()
        conn.close()
        
        if user and check_pass(user[4], password):
            session['user_id'] = user[0]
            session['username'] = user[1]
            session['display_name'] = user[2]
            session['is_admin'] = bool(user[5])
            session['theme'] = user[10] if user[10] else 'light'
            
            # Update last login
            conn = sqlite3.connect(DATABASE)
            c = conn.cursor()
            c.execute('UPDATE users SET last_login = ? WHERE id = ?', 
                     (datetime.now().isoformat(), user[0]))
            conn.commit()
            conn.close()
            
            # Log analytics
            DatabaseManager.log_analytics('login', user[0])
            
            if bool(user[5]):
                return redirect('/admin')
            return redirect('/student')
    
    # Enhanced login page
    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
    <title>Vibhuayu Technologies - Enhanced PD Assessment</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        :root {
            --primary-color: #667eea;
            --secondary-color: #764ba2;
            --success-color: #10b981;
            --warning-color: #f59e0b;
            --error-color: #ef4444;
            --bg-primary: #0f172a;
            --bg-secondary: #1e293b;
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --surface: rgba(255, 255, 255, 0.98);
            --border: #e2e8f0;
        }
        
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            background: linear-gradient(135deg, var(--bg-primary) 0%, var(--bg-secondary) 100%); 
            min-height: 100vh; 
            display: flex; 
            align-items: center; 
            justify-content: center; 
            position: relative;
            overflow-x: hidden;
        }
        
        body::before {
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0; bottom: 0;
            background: 
                radial-gradient(circle at 30% 40%, rgba(102, 126, 234, 0.3) 0%, transparent 50%),
                radial-gradient(circle at 80% 80%, rgba(118, 75, 162, 0.15) 0%, transparent 50%);
            z-index: 1;
        }
        
        .container {
            position: relative; z-index: 2;
            background: var(--surface);
            backdrop-filter: blur(20px);
            border-radius: 24px;
            padding: 50px 40px;
            width: min(450px, 90vw);
            box-shadow: 0 25px 50px rgba(0, 0, 0, 0.25);
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        .logo-section {
            text-align: center;
            margin-bottom: 35px;
        }
        
        .logo {
            width: 80px; height: 80px;
            margin: 0 auto 20px;
            background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
            border-radius: 20px;
            display: flex; align-items: center; justify-content: center;
            color: white; font-size: 36px; font-weight: 900;
            box-shadow: 0 10px 30px rgba(102, 126, 234, 0.3);
            position: relative; overflow: hidden;
        }
px;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 20px; margin-bottom: 30px;
        }
        
        .stat-card {
            background: var(--surface);
            padding: 25px; border-radius: 20px; text-align: center;
            box-shadow: 0 8px 25px rgba(0,0,0,0.1);
            transition: transform 0.3s ease;
        }
        
        .stat-card:hover { transform: translateY(-5px); }
        
        .stat-number {
            font-size: 36px; font-weight: 800;
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            margin-bottom: 8px; line-height: 1;
        }
        
        .stat-label {
            color: var(--text-secondary); font-weight: 600;
            font-size: 14px; text-transform: uppercase; letter-spacing: 1px;
        }
        
        .stat-subtitle {
            color: var(--text-secondary); font-size: 12px;
            margin-top: 5px;
        }
        
        .main-section {
            background: var(--surface);
            border-radius: 24px; padding: 35px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }
        
        .section-header {
            display: flex; justify-content: space-between; align-items: center;
            margin-bottom: 30px;
        }
        
        .section-title {
            color: var(--text-primary); font-size: 28px; font-weight: 700;
            display: flex; align-items: center; gap: 12px;
        }
        
        .assignment-card {
            background: linear-gradient(135deg, #f8fafc, #f1f5f9);
            border-radius: 16px; padding: 25px; margin: 20px 0;
            box-shadow: 0 4px 15px rgba(0,0,0,0.05);
            transition: all 0.3s ease; position: relative;
            overflow: hidden;
        }
        
        .assignment-card::before {
            content: ''; position: absolute; top: 0; left: 0;
            width: 4px; height: 100%;
        }
        
        .assignment-card.pending::before { background: var(--primary); }
        .assignment-card.submitted::before { background: var(--warning); }
        .assignment-card.completed::before { background: var(--success); }
        
        .assignment-card:hover {
            transform: translateY(-3px);
            box-shadow: 0 8px 25px rgba(0,0,0,0.1);
        }
        
        .assignment-header {
            display: flex; justify-content: space-between; align-items: center;
            margin-bottom: 15px;
        }
        
        .assignment-header h3 {
            color: var(--text-primary); font-size: 20px; margin: 0;
        }
        
        .score-display {
            background: var(--success); color: white;
            padding: 6px 15px; border-radius: 20px;
            font-weight: 700; font-size: 16px;
        }
        
        .due-date {
            background: var(--primary); color: white;
            padding: 6px 15px; border-radius: 20px;
            font-weight: 600; font-size: 14px;
        }
        
        .status-display {
            background: var(--warning); color: white;
            padding: 6px 15px; border-radius: 20px;
            font-weight: 600; font-size: 14px;
        }
        
        .assignment-meta {
            color: var(--text-secondary); font-size: 14px;
            margin-bottom: 15px; line-height: 1.5;
        }
        
        .start-btn {
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            color: white; padding: 12px 25px; text-decoration: none;
            border-radius: 10px; display: inline-block;
            font-weight: 600; transition: all 0.3s ease;
        }
        
        .start-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 20px rgba(102, 126, 234, 0.4);
        }
        
        .status-badge {
            padding: 8px 16px; border-radius: 20px;
            font-size: 12px; font-weight: 600;
            display: inline-block; margin-top: 10px;
        }
        
        .status-badge.pending {
            background: rgba(102, 126, 234, 0.1); color: var(--primary);
        }
        
        .status-badge.submitted {
            background: rgba(245, 158, 11, 0.1); color: var(--warning);
        }
        
        .status-badge.completed {
            background: rgba(16, 185, 129, 0.1); color: var(--success);
        }
        
        .no-assignments {
            text-align: center; padding: 80px 20px;
            color: var(--text-secondary);
        }
        
        .empty-icon {
            font-size: 64px; margin-bottom: 20px; opacity: 0.7;
        }
        
        .progress-section {
            background: linear-gradient(135deg, #f0f9ff, #e0f2fe);
            border-radius: 16px; padding: 25px; margin-top: 30px;
        }
        
        .progress-title {
            color: var(--text-primary); font-weight: 700;
            margin-bottom: 15px; text-align: center;
        }
        
        .progress-bar {
            background: #e2e8f0; height: 8px; border-radius: 4px;
            overflow: hidden; margin-bottom: 15px;
        }
        
        .progress-fill {
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            height: 100%; transition: width 0.3s ease;
        }
        
        .progress-text {
            text-align: center; color: var(--text-secondary);
            font-size: 14px; font-weight: 600;
        }
        
        @media (max-width: 768px) {
            .header-content {
                flex-direction: column; gap: 15px; text-align: center;
            }
            
            .stats-grid {
                grid-template-columns: repeat(2, 1fr);
            }
            
            .assignment-header {
                flex-direction: column; align-items: flex-start; gap: 10px;
            }
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="header-content">
            <div class="user-info">
                <div class="user-avatar">{{ user[2][:1].upper() }}</div>
                <div class="welcome-text">
                    <h1>Welcome back, {{ user[2] }}! 👋</h1>
                    <p>{{ user[6] }}+ years experience in Physical Design</p>
                </div>
            </div>
            <div class="nav-actions">
                <a href="/logout" class="nav-btn">🚪 Logout</a>
            </div>
        </div>
    </div>
    
    <div class="container">
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-number">{{ total_assignments }}</div>
                <div class="stat-label">Total Assigned</div>
                <div class="stat-subtitle">All assessments</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ pending }}</div>
                <div class="stat-label">Pending</div>
                <div class="stat-subtitle">Ready to start</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ completed }}</div>
                <div class="stat-label">Completed</div>
                <div class="stat-subtitle">Graded assessments</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ "%.1f"|format(avg_score) }}</div>
                <div class="stat-label">Average Score</div>
                <div class="stat-subtitle">Out of 10 points</div>
            </div>
        </div>
        
        <div class="main-section">
            <div class="section-header">
                <h2 class="section-title">📋 My Assessments</h2>
            </div>
            
            <div id="assignmentsContainer">
                {{ assignments_html|safe }}
            </div>
        </div>
        
        {% if completed > 0 %}
        <div class="progress-section">
            <div class="progress-title">📊 Your Progress</div>
            <div class="progress-bar">
                <div class="progress-fill" style="width: {{ (completed / total_assignments * 100)|round }}%;"></div>
            </div>
            <div class="progress-text">
                {{ completed }} of {{ total_assignments }} assessments completed ({{ (completed / total_assignments * 100)|round }}%)
            </div>
        </div>
        {% endif %}
    </div>
</body>
</html>""", 
    user=user,
    assignments_html=assignments_html,
    total_assignments=total_assignments,
    completed=completed,
    pending=pending,
    avg_score=avg_score
    )

@app.route('/student/test/<assignment_id>', methods=['GET', 'POST'])
def student_test(assignment_id):
    if not session.get('user_id') or session.get('is_admin'):
        return redirect('/login')
    
    user_id = session['user_id']
    
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    # Get assignment
    c.execute('SELECT * FROM assignments WHERE id = ? AND engineer_id = ?', (assignment_id, user_id))
    assignment = c.fetchone()
    
    if not assignment:
        conn.close()
        return redirect('/student')
    
    # Check if already submitted
    c.execute('SELECT * FROM submissions WHERE assignment_id = ? AND engineer_id = ?', (assignment_id, user_id))
    existing_submission = c.fetchone()
    
    if existing_submission:
        conn.close()
        return redirect('/student')
    
    questions = json.loads(assignment[3])
    
    # Handle submission
    if request.method == 'POST':
        answers = {}
        for i in range(len(questions)):
            answer = request.form.get(f'answer_{i}', '').strip()
            if answer:
                answers[str(i)] = answer
        
        if len(answers) >= 15:
            # Auto-score answers
            auto_scores = {}
            for i, answer in answers.items():
                if answer:
                    score_analysis = scoring_system.analyze_answer_comprehensive(
                        questions[int(i)], answer, assignment[2]
                    )
                    auto_scores[i] = score_analysis
            
            # Create submission
            submission_id = f"SUB_{assignment_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            c.execute('''
                INSERT INTO submissions 
                (id, assignment_id, engineer_id, answers, submitted_date, auto_scores, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (submission_id, assignment_id, user_id, json.dumps(answers),
                  datetime.now().isoformat(), json.dumps(auto_scores), 'submitted'))
            
            conn.commit()
            
            # Log analytics
            DatabaseManager.log_analytics('submission_created', user_id, {
                'assignment_id': assignment_id,
                'answers_count': len(answers),
                'topic': assignment[2]
            })
        
        conn.close()
        return redirect('/student')
    
    conn.close()
    
    # Build questions HTML
    questions_html = ''
    for i, question in enumerate(questions):
        questions_html += f'''
        <div class="question-card" data-question="{i}">
            <div class="question-header">
                <div class="question-number">Question {i+1} of {len(questions)}</div>
                <div class="topic-badge">{assignment[2].upper()}</div>
            </div>
            
            <div class="question-content">
                <div class="question-text">{question}</div>
                
                <div class="answer-section">
                    <label for="answer_{i}">Your Answer:</label>
                    <textarea id="answer_{i}" name="answer_{i}" 
                             placeholder="Provide a detailed technical answer..." 
                             required minlength="20"></textarea>
                    <div class="char-counter">
                        <span id="count_{i}">0</span> characters
                        <span class="min-requirement">(minimum 20 required)</span>
                    </div>
                </div>
            </div>
        </div>'''
    
    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
    <title>{{ assignment[2].upper() }} Assessment - Enhanced Experience</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        :root {
            --primary: #667eea;
            --secondary: #764ba2;
            --success: #10b981;
            --warning: #f59e0b;
            --error: #ef4444;
            --surface: rgba(255, 255, 255, 0.98);
        }
        
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%);
            min-height: 100vh;
        }
        
        .test-header {
            background: rgba(255,255,255,0.15);
            backdrop-filter: blur(20px);
            color: white; padding: 20px 0;
            position: sticky; top: 0; z-index: 100;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
        }
        
        .header-content {
            max-width: 1000px; margin: 0 auto; padding: 0 20px;
            display: flex; justify-content: space-between; align-items: center;
        }
        
        .test-info h1 {
            font-size: 24px; font-weight: 700; margin-bottom: 5px;
        }
        
        .test-meta {
            opacity: 0.9; font-size: 14px;
        }
        
        .progress-container {
            display: flex; align-items: center; gap: 15px;
        }
        
        .progress-circle {
            width: 60px; height: 60px;
            border-radius: 50%; background: rgba(255,255,255,0.2);
            display: flex; align-items: center; justify-content: center;
            font-weight: 700; font-size: 14px;
            border: 3px solid rgba(255,255,255,0.3);
        }
        
        .container {
            max-width: 1000px; margin: 20px auto; padding: 0 20px;
        }
        
        .test-overview {
            background: var(--surface); border-radius: 20px;
            padding: 30px; margin-bottom: 25px;
            box-shadow: 0 8px 25px rgba(0,0,0,0.1);
            text-align: center;
        }
        
        .overview-grid {
            display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 20px; margin-top: 20px;
        }
        
        .overview-item {
            text-align: center;
        }
        
        .overview-value {
            font-size: 24px; font-weight: 700; color: var(--primary);
            margin-bottom: 5px;
        }
        
        .overview-label {
            color: #64748b; font-size: 14px; font-weight: 600;
        }
        
        .progress-tracker {
            background: var(--surface); border-radius: 16px;
            padding: 20px; margin-bottom: 25px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }
        
        .progress-bar {
            background: #e2e8f0; height: 8px; border-radius: 4px;
            overflow: hidden; margin: 15px 0;
        }
        
        .progress-fill {
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            height: 100%; width: 0%; transition: width 0.3s ease;
        }
        
        .progress-text {
            display: flex; justify-content: space-between; align-items: center;
            font-weight: 600; color: #64748b;
        }
        
        .question-card {
            background: var(--surface); border-radius: 20px;
            padding: 30px; margin: 25px 0;
            box-shadow: 0 8px 25px rgba(0,0,0,0.1);
            transition: all 0.3s ease;
        }
        
        .question-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 12px 35px rgba(0,0,0,0.15);
        }
        
        .question-header {
            display: flex; justify-content: space-between; align-items: center;
            margin-bottom: 25px;
        }
        
        .question-number {
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            color: white; padding: 10px 20px; border-radius: 25px;
            font-weight: 700; font-size: 14px;
        }
        
        .topic-badge {
            background: #f1f5f9; color: #64748b;
            padding: 8px 16px; border-radius: 20px;
            font-size: 12px; font-weight: 600; text-transform: uppercase;
        }
        
        .question-content {
            line-height: 1.6;
        }
        
        .question-text {
            background: linear-gradient(135deg, #f8fafc, #f1f5f9);
            padding: 25px; border-radius: 16px; margin-bottom: 25px;
            border-left: 4px solid var(--primary);
            font-size: 16px; line-height: 1.7;
        }
        
        .answer-section label {
            display: block; margin-bottom: 10px;
            font-weight: 600; color: #374151; font-size: 16px;
        }
        
        textarea {
            width: 100%; min-height: 140px; padding: 20px;
            border: 2px solid #e5e7eb; border-radius: 16px;
            font-size: 15px; font-family: inherit; resize: vertical;
            transition: all 0.3s ease; line-height: 1.6;
        }
        
        textarea:focus {
            outline: none; border-color: var(--primary);
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }
        
        .char-counter {
            display: flex; justify-content: space-between; align-items: center;
            margin-top: 8px; font-size: 13px;
        }
        
        .min-requirement {
            color: #64748b;
        }
        
        .submit-section {
            background: var(--surface); border-radius: 20px;
            padding: 40px; margin-top: 40px; text-align: center;
            box-shadow: 0 8px 25px rgba(0,0,0,0.1);
        }
        
        .warning-box {
            background: #fef3c7; border: 2px solid #f59e0b;
            padding: 20px; border-radius: 16px; margin-bottom: 25px;
            display: flex; align-items: center; gap: 15px;
        }
        
        .warning-icon {
            font-size: 24px;
        }
        
        .btn {
            padding: 15px 30px; border: none; border-radius: 12px;
            font-weight: 600; cursor: pointer; margin: 8px;
            text-decoration: none; display: inline-block;
            transition: all 0.3s ease; font-size: 16px;
        }
        
        .btn-primary {
            background: linear-gradient(135deg, var(--success), #059669);
            color: white;
        }
        
        .btn-secondary {
            background: #6b7280; color: white;
        }
        
        .btn:hover { transform: translateY(-2px); }
        
        .btn:disabled {
            opacity: 0.6; cursor: not-allowed;
            transform: none !important;
        }
        
        @media (max-width: 768px) {
            .header-content {
                flex-direction: column; gap: 15px; text-align: center;
            }
            
            .overview-grid {
                grid-template-columns: repeat(2, 1fr);
            }
            
            .question-header {
                flex-direction: column; gap: 10px; align-items: flex-start;
            }
        }
    </style>
</head>
<body>
    <div class="test-header">
        <div class="header-content">
            <div class="test-info">
                <h1>📝 {{ assignment[2].upper() }} Assessment</h1>
                <div class="test-meta">Enhanced Physical Design Evaluation</div>
            </div>
            <div class="progress-container">
                <div class="progress-circle" id="progressCircle">0%</div>
            </div>
        </div>
    </div>
    
    <div class="container">
        <div class="test-overview">
            <h2>📋 Assessment Overview</h2>
            <div class="overview-grid">
                <div class="overview-item">
                    <div class="overview-value">{{ len(questions) }}</div>
                    <div class="overview-label">Questions</div>
                </div>
                <div class="overview-item">
                    <div class="overview-value">{{ len(questions) * 10 }}</div>
                    <div class="overview-label">Max Points</div>
                </div>
                <div class="overview-item">
                    <div class="overview-value">{{ assignment[5][:10] }}</div>
                    <div class="overview-label">Due Date</div>
                </div>
                <div class="overview-item">
                    <div class="overview-value">{{ assignment[2].upper() }}</div>
                    <div class="overview-label">Topic</div>
                </div>
            </div>
        </div>
        
        <div class="progress-tracker">
            <div class="progress-text">
                <span>Progress</span>
                <span id="progressText">0 of {{ len(questions) }} answered</span>
            </div>
            <div class="progress-bar">
                <div class="progress-fill" id="progressBar"></div>
            </div>
        </div>
        
        <form method="POST" id="assessmentForm">
            {{ questions_html|safe }}
            
            <div class="submit-section">
                <div class="warning-box">
                    <div class="warning-icon">⚠️</div>
                    <div>
                        <strong>Important Notice:</strong> Review all answers carefully before submitting. 
                        You cannot edit your responses after submission. Minimum 15 questions must be answered.
                    </div>
                </div>
                
                <button type="submit" class="btn btn-primary" id="submitBtn" disabled>
                    🚀 Submit Assessment
                </button>
                <a href="/student" class="btn btn-secondary">💾 Save & Exit Later</a>
            </div>
        </form>
    </div>
    
    <script>
        const totalQuestions = {{ len(questions) }};
        const textareas = document.querySelectorAll('textarea');
        const progressBar = document.getElementById('progressBar');
        const progressText = document.getElementById('progressText');
        const progressCircle = document.getElementById('progressCircle');
        const submitBtn = document.getElementById('submitBtn');
        
        // Initialize
        setupEventListeners();
        loadAutoSavedData();
        updateProgress();
        
        function setupEventListeners() {
            textareas.forEach((textarea, index) => {
                const counter = document.getElementById(`count_${index}`);
                
                textarea.addEventListener('input', function() {
                    const length = this.value.length;
                    counter.textContent = length;
                    
                    // Color coding for minimum requirement
                    if (length < 20) {
                        counter.style.color = '#ef4444';
                    } else if (length < 50) {
                        counter.style.color = '#f59e0b';
                    } else {
                        counter.style.color = '#10b981';
                    }
                    
                    updateProgress();
                    autoSave();
                });
                
                // Auto-resize textarea
                textarea.addEventListener('input', function() {
                    this.style.height = 'auto';
                    this.style.height = Math.max(140, this.scrollHeight) + 'px';
                });
            });
            
            // Form submission
            document.getElementById('assessmentForm').addEventListener('submit', function(e) {
                const answeredCount = getAnsweredCount();
                
                if (answeredCount < 15) {
                    e.preventDefault();
                    alert(`Please answer at least 15 questions. Currently answered: ${answeredCount}`);
                    return false;
                }
                
                const confirmed = confirm(
                    `Are you sure you want to submit your assessment?\\n\\n` +
                    `• Questions answered: ${answeredCount}/${totalQuestions}\\n` +
                    `• This action cannot be undone\\n` +
                    `• Your responses will be final\\n\\n` +
                    `Click OK to submit or Cancel to continue editing.`
                );
                
                if (!confirmed) {
                    e.preventDefault();
                    return false;
                }
                
                // Clear auto-saved data
                clearAutoSavedData();
            });
        }
        
        function updateProgress() {
            const answeredCount = getAnsweredCount();
            const percentage = (answeredCount / totalQuestions) * 100;
            
            progressBar.style.width = percentage + '%';
            progressText.textContent = `${answeredCount} of ${totalQuestions} answered`;
            progressCircle.textContent = Math.round(percentage) + '%';
            
            // Enable submit if at least 15 questions answered
            const meetsMinimum = answeredCount >= 15;
            submitBtn.disabled = !meetsMinimum;
            
            if (meetsMinimum) {
                submitBtn.style.opacity = '1';
                submitBtn.textContent = `🚀 Submit Assessment (${answeredCount}/${totalQuestions})`;
            } else {
                submitBtn.style.opacity = '0.6';
                submitBtn.textContent = `Answer ${15 - answeredCount} more to submit`;
            }
        }
        
        function getAnsweredCount() {
            return Array.from(textareas).filter(ta => ta.value.trim().length >= 20).length;
        }
        
        function autoSave() {
            const formData = {};
            textareas.forEach((textarea, index) => {
                formData[`answer_${index}`] = textarea.value;
            });
            
            localStorage.setItem(`assessment_{{ assignment[0] }}`, JSON.stringify({
                data: formData,
                timestamp: Date.now()
            }));
        }
        
        function loadAutoSavedData() {
            const saved = localStorage.getItem(`assessment_{{ assignment[0] }}`);
            if (saved) {
                try {
                    const { data } = JSON.parse(saved);
                    
                    textareas.forEach((textarea, index) => {
                        const savedValue = data[`answer_${index}`];
                        if (savedValue) {
                            textarea.value = savedValue;
                            textarea.dispatchEvent(new Event('input'));
                        }
                    });
                    
                    console.log('✅ Auto-saved data loaded');
                } catch (e) {
                    console.warn('Failed to load auto-saved data');
                }
            }
        }
        
        function clearAutoSavedData() {
            localStorage.removeItem(`assessment_{{ assignment[0] }}`);
        }
        
        // Auto-save every 30 seconds
        setInterval(() => {
            if (getAnsweredCount() > 0) {
                autoSave();
            }
        }, 30000);
        
        // Prevent accidental page leave
        window.addEventListener('beforeunload', function(e) {
            const answeredCount = getAnsweredCount();
            if (answeredCount > 0) {
                e.preventDefault();
                e.returnValue = 'You have unsaved answers. Are you sure you want to leave?';
                return e.returnValue;
            }
        });
        
        console.log('🚀 Enhanced assessment experience loaded');
        console.log(`📊 Assessment: {{ assignment[2].upper() }} with ${totalQuestions} questions`);
    </script>
</body>
</html>""", 
    assignment=assignment,
    questions=questions,
    questions_html=questions_html
    )

# Additional utility routes
@app.route('/admin/stats')
def admin_stats():
    if not session.get('is_admin'):
        return jsonify({'error': 'Unauthorized'}), 403
    
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    c.execute('SELECT COUNT(*) FROM users WHERE is_admin = 0')
    engineers = c.fetchone()[0]
    
    c.execute('SELECT COUNT(*) FROM assignments')
    assignments = c.fetchone()[0]
    
    c.execute('SELECT COUNT(*) FROM submissions WHERE status = "submitted"')
    pending = c." if suggested_score >= 5 else "#ef4444"
        
        questions_html += f'''
        <div class="question-review-card">
            <div class="question-header">
                <h3>Question {i+1}</h3>
                <div class="ai-score-badge" style="background: {color};">
                    AI Score: {suggested_score}/10
                </div>
            </div>
            
            <div class="question-text">
                <strong>Question:</strong><br>
                {question}
            </div>
            
            <div class="answer-section">
                <strong>Engineer's Answer:</strong>
                <div class="answer-text">{answer}</div>
            </div>
            
            <div class="scoring-analysis">
                <div class="score-breakdown">
                    <h4>AI Analysis Breakdown:</h4>
                    <div class="breakdown-grid">
                        <div class="breakdown-item">
                            <span>Technical:</span>
                            <span>{breakdown['technical']}/10</span>
                        </div>
                        <div class="breakdown-item">
                            <span>Depth:</span>
                            <span>{breakdown['depth']}/10</span>
                        </div>
                        <div class="breakdown-item">
                            <span>Methodology:</span>
                            <span>{breakdown['methodology']}/10</span>
                        </div>
                        <div class="breakdown-item">
                            <span>Clarity:</span>
                            <span>{breakdown['clarity']}/10</span>
                        </div>
                    </div>
                </div>
                
                <div class="ai-suggestions">
                    <h4>Improvement Suggestions:</h4>
                    <ul>
                        {''.join([f'<li>{suggestion}</li>' for suggestion in suggestions[:3]])}
                    </ul>
                </div>
            </div>
            
            <div class="manual-grading">
                <div class="grade-input">
                    <label>Your Score:</label>
                    <input type="number" name="score_{i}" min="0" max="10" step="0.1" 
                           value="{suggested_score}" class="score-input">
                    <button type="button" onclick="this.previousElementSibling.value='{suggested_score}'" 
                            class="use-ai-btn">Use AI Score</button>
                </div>
                <div class="feedback-input">
                    <label>Additional Feedback:</label>
                    <textarea name="feedback_{i}" placeholder="Optional: Add specific feedback for this answer..."></textarea>
                </div>
            </div>
        </div>'''
    
    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
    <title>Review Assessment - Enhanced Admin</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        :root {
            --primary: #667eea;
            --secondary: #764ba2;
            --success: #10b981;
            --warning: #f59e0b;
            --error: #ef4444;
            --surface: #ffffff;
            --bg-light: #f8fafc;
        }
        
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
            min-height: 100vh;
        }
        
        .header {
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            color: white; padding: 20px 0;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
        }
        
        .header-content {
            max-width: 1200px; margin: 0 auto; padding: 0 20px;
            display: flex; justify-content: space-between; align-items: center;
        }
        
        .container {
            max-width: 1200px; margin: 20px auto; padding: 0 20px;
        }
        
        .submission-info {
            background: var(--surface); border-radius: 16px;
            padding: 25px; margin-bottom: 25px;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
        }
        
        .info-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
        }
        
        .info-item {
            text-align: center;
        }
        
        .info-value {
            font-size: 24px; font-weight: 700;
            color: var(--primary); margin-bottom: 5px;
        }
        
        .info-label {
            color: #64748b; font-size: 14px; font-weight: 600;
        }
        
        .question-review-card {
            background: var(--surface); border-radius: 16px;
            padding: 25px; margin: 20px 0;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
            border-left: 4px solid var(--primary);
        }
        
        .question-header {
            display: flex; justify-content: space-between;
            align-items: center; margin-bottom: 20px;
        }
        
        .question-header h3 {
            color: #1e293b; font-size: 18px;
        }
        
        .ai-score-badge {
            color: white; padding: 6px 15px;
            border-radius: 20px; font-weight: 600; font-size: 14px;
        }
        
        .question-text {
            background: var(--bg-light); padding: 15px;
            border-radius: 8px; margin-bottom: 15px;
            border-left: 3px solid var(--primary);
        }
        
        .answer-section {
            margin-bottom: 20px;
        }
        
        .answer-text {
            background: #fefefe; border: 1px solid #e2e8f0;
            padding: 15px; border-radius: 8px; margin-top: 8px;
            line-height: 1.6; white-space: pre-wrap;
            max-height: 200px; overflow-y: auto;
        }
        
        .scoring-analysis {
            background: var(--bg-light); border-radius: 12px;
            padding: 20px; margin-bottom: 20px;
        }
        
        .breakdown-grid {
            display: grid; grid-template-columns: repeat(2, 1fr);
            gap: 10px; margin-top: 10px;
        }
        
        .breakdown-item {
            display: flex; justify-content: space-between;
            padding: 8px 12px; background: white; border-radius: 6px;
        }
        
        .ai-suggestions {
            margin-top: 15px;
        }
        
        .ai-suggestions ul {
            margin-top: 8px; padding-left: 20px;
        }
        
        .ai-suggestions li {
            margin-bottom: 5px; color: #64748b;
        }
        
        .manual-grading {
            display: grid; grid-template-columns: 1fr 2fr; gap: 20px;
            padding-top: 20px; border-top: 1px solid #e2e8f0;
        }
        
        .grade-input {
            display: flex; flex-direction: column; gap: 10px;
        }
        
        .score-input {
            padding: 8px 12px; border: 2px solid #e2e8f0;
            border-radius: 6px; font-size: 16px; width: 80px;
        }
        
        .use-ai-btn {
            padding: 6px 12px; background: var(--primary);
            color: white; border: none; border-radius: 6px;
            cursor: pointer; font-size: 12px;
        }
        
        .feedback-input textarea {
            width: 100%; height: 80px; padding: 10px;
            border: 2px solid #e2e8f0; border-radius: 6px;
            resize: vertical; font-family: inherit;
        }
        
        .submit-section {
            background: var(--surface); border-radius: 16px;
            padding: 25px; margin-top: 30px; text-align: center;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
        }
        
        .btn {
            padding: 12px 25px; border: none; border-radius: 8px;
            font-weight: 600; cursor: pointer; margin: 5px;
            text-decoration: none; display: inline-block;
            transition: all 0.3s ease;
        }
        
        .btn-primary {
            background: linear-gradient(135deg, var(--success), #059669);
            color: white;
        }
        
        .btn-secondary {
            background: #6b7280; color: white;
        }
        
        .btn:hover { transform: translateY(-2px); }
        
        .total-calculator {
            background: var(--primary); color: white;
            padding: 15px; border-radius: 12px; margin-bottom: 20px;
            text-align: center; font-weight: 600;
        }
        
        @media (max-width: 768px) {
            .manual-grading { grid-template-columns: 1fr; }
            .breakdown-grid { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="header-content">
            <h1>📝 Review Assessment</h1>
            <a href="/admin" class="btn btn-secondary">← Back to Dashboard</a>
        </div>
    </div>
    
    <div class="container">
        <div class="submission-info">
            <div class="info-grid">
                <div class="info-item">
                    <div class="info-value">{{ submission[13] }}</div>
                    <div class="info-label">Engineer</div>
                </div>
                <div class="info-item">
                    <div class="info-value">{{ submission[11].upper() }}</div>
                    <div class="info-label">Topic</div>
                </div>
                <div class="info-item">
                    <div class="info-value">{{ len(questions) }}</div>
                    <div class="info-label">Questions</div>
                </div>
                <div class="info-item">
                    <div class="info-value">{{ submission[4][:10] }}</div>
                    <div class="info-label">Submitted</div>
                </div>
            </div>
        </div>
        
        <form method="POST" id="gradingForm">
            <div class="total-calculator">
                <span>Total Score: </span>
                <span id="totalScore">0</span>
                <span>/{{ len(questions) * 10 }} points</span>
                <span style="margin-left: 20px;">Average: </span>
                <span id="averageScore">0.0</span>
                <span>/10</span>
            </div>
            
            {{ questions_html|safe }}
            
            <div class="submit-section">
                <div style="background: #fef3c7; padding: 15px; border-radius: 8px; margin-bottom: 20px; color: #92400e;">
                    ⚠️ <strong>Review carefully:</strong> Grades will be final once submitted.
                </div>
                <button type="submit" class="btn btn-primary">✅ Submit Final Grades</button>
                <a href="/admin" class="btn btn-secondary">Cancel Review</a>
            </div>
        </form>
    </div>
    
    <script>
        // Calculate total score dynamically
        function updateTotal() {
            const scoreInputs = document.querySelectorAll('.score-input');
            let total = 0;
            let count = 0;
            
            scoreInputs.forEach(input => {
                const value = parseFloat(input.value) || 0;
                total += value;
                count++;
            });
            
            document.getElementById('totalScore').textContent = total.toFixed(1);
            document.getElementById('averageScore').textContent = (total / count).toFixed(1);
        }
        
        // Add event listeners to all score inputs
        document.querySelectorAll('.score-input').forEach(input => {
            input.addEventListener('input', updateTotal);
        });
        
        // Initial calculation
        updateTotal();
        
        // Form validation
        document.getElementById('gradingForm').addEventListener('submit', function(e) {
            if (!confirm('Are you sure you want to submit these grades? This action cannot be undone.')) {
                e.preventDefault();
            }
        });
    </script>
</body>
</html>""", 
    submission=submission,
    questions=questions,
    answers=answers,
    auto_scores=auto_scores,
    questions_html=questions_html
    )

@app.route('/admin/analytics')
def admin_analytics():
    if not session.get('is_admin'):
        return redirect('/login')
    
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    # Comprehensive analytics queries
    analytics_data = {}
    
    # Topic performance
    c.execute('''
        SELECT 
            a.topic,
            COUNT(s.id) as submissions,
            AVG(CAST(s.total_score as FLOAT)) as avg_score,
            MAX(CAST(s.total_score as FLOAT)) as max_score,
            MIN(CAST(s.total_score as FLOAT)) as min_score
        FROM assignments a
        LEFT JOIN submissions s ON a.id = s.assignment_id AND s.status = 'graded'
        GROUP BY a.topic
    ''')
    analytics_data['topic_performance'] = c.fetchall()
    
    # Engineer performance
    c.execute('''
        SELECT 
            u.display_name,
            u.experience,
            COUNT(s.id) as completed,
            AVG(CAST(s.total_score as FLOAT)) as avg_score,
            MAX(CAST(s.total_score as FLOAT)) as best_score
        FROM users u
        LEFT JOIN submissions s ON u.id = s.engineer_id AND s.status = 'graded'
        WHERE u.is_admin = 0
        GROUP BY u.id
        ORDER BY avg_score DESC
    ''')
    analytics_data['engineer_performance'] = c.fetchall()
    
    conn.close()
    
    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
    <title>Performance Analytics - Enhanced Admin</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.9.1/chart.min.js"></script>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
            margin: 0; min-height: 100vh; color: white;
        }
        
        .analytics-container {
            max-width: 1400px; margin: 0 auto; padding: 20px;
        }
        
        .analytics-grid {
            display: grid; grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 25px; margin: 25px 0;
        }
        
        .chart-card {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 20px; padding: 25px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
        }
        
        .chart-title {
            color: #1e293b; font-size: 18px; font-weight: 700;
            margin-bottom: 20px; text-align: center;
        }
        
        .stats-overview {
            display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px; margin-bottom: 30px;
        }
        
        .stat-box {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 16px; padding: 20px; text-align: center;
            backdrop-filter: blur(10px);
        }
        
        .stat-number {
            font-size: 32px; font-weight: 800; margin-bottom: 5px;
        }
        
        .performance-table {
            width: 100%; border-collapse: collapse; margin-top: 15px;
        }
        
        .performance-table th,
        .performance-table td {
            padding: 12px; text-align: left; border-bottom: 1px solid #e2e8f0;
        }
        
        .performance-table th {
            background: #f8fafc; font-weight: 600; color: #1e293b;
        }
        
        .score-badge {
            padding: 4px 12px; border-radius: 20px; font-weight: 600;
            font-size: 12px; color: white;
        }
        
        .score-excellent { background: #10b981; }
        .score-good { background: #f59e0b; }
        .score-needs-improvement { background: #ef4444; }
    </style>
</head>
<body>
    <div class="analytics-container">
        <div style="text-align: center; margin-bottom: 30px;">
            <h1 style="font-size: 36px; margin-bottom: 10px;">📊 Performance Analytics</h1>
            <p style="color: #94a3b8;">Comprehensive insights into assessment performance</p>
            <a href="/admin" style="color: #667eea; text-decoration: none;">← Back to Dashboard</a>
        </div>
        
        <div class="stats-overview">
            <div class="stat-box">
                <div class="stat-number" style="color: #667eea;">{{ analytics_data.topic_performance|length }}</div>
                <div>Active Topics</div>
            </div>
            <div class="stat-box">
                <div class="stat-number" style="color: #10b981;">{{ analytics_data.engineer_performance|length }}</div>
                <div>Engineers</div>
            </div>
            <div class="stat-box">
                <div class="stat-number" style="color: #f59e0b;">
                    {% set total_submissions = analytics_data.topic_performance|map(attribute=1)|sum %}
                    {{ total_submissions }}
                </div>
                <div>Total Submissions</div>
            </div>
            <div class="stat-box">
                <div class="stat-number" style="color: #8b5cf6;">
                    {% if analytics_data.topic_performance %}
                        {% set avg_score = (analytics_data.topic_performance|map(attribute=2)|sum) / (analytics_data.topic_performance|length) %}
                        {{ "%.1f"|format(avg_score) }}
                    {% else %}
                        0.0
                    {% endif %}
                </div>
                <div>Average Score</div>
            </div>
        </div>
        
        <div class="analytics-grid">
            <div class="chart-card">
                <div class="chart-title">📈 Topic Performance Overview</div>
                <canvas id="topicChart" width="400" height="300"></canvas>
            </div>
            
            <div class="chart-card">
                <div class="chart-title">👥 Engineer Performance Distribution</div>
                <canvas id="engineerChart" width="400" height="300"></canvas>
            </div>
        </div>
        
        <div class="chart-card">
            <div class="chart-title">🏆 Top Performers</div>
            <table class="performance-table">
                <thead>
                    <tr>
                        <th>Engineer</th>
                        <th>Experience</th>
                        <th>Completed</th>
                        <th>Average Score</th>
                        <th>Best Score</th>
                        <th>Performance</th>
                    </tr>
                </thead>
                <tbody>
                    {% for engineer in analytics_data.engineer_performance[:10] %}
                    <tr>
                        <td><strong>{{ engineer[0] }}</strong></td>
                        <td>{{ engineer[1] }}y</td>
                        <td>{{ engineer[2] }}</td>
                        <td>{{ "%.1f"|format(engineer[3] or 0) }}</td>
                        <td>{{ "%.1f"|format(engineer[4] or 0) }}</td>
                        <td>
                            {% set avg = engineer[3] or 0 %}
                            {% if avg >= 8 %}
                                <span class="score-badge score-excellent">Excellent</span>
                            {% elif avg >= 6 %}
                                <span class="score-badge score-good">Good</span>
                            {% else %}
                                <span class="score-badge score-needs-improvement">Needs Improvement</span>
                            {% endif %}
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
    
    <script>
        // Topic Performance Chart
        const topicData = {{ analytics_data.topic_performance|tojson }};
        const topicLabels = topicData.map(item => item[0].toUpperCase());
        const topicScores = topicData.map(item => item[2] || 0);
        
        new Chart(document.getElementById('topicChart'), {
            type: 'bar',
            data: {
                labels: topicLabels,
                datasets: [{
                    label: 'Average Score',
                    data: topicScores,
                    backgroundColor: ['#667eea', '#10b981', '#f59e0b'],
                    borderColor: ['#4f46e5', '#059669', '#d97706'],
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 10,
                        title: { display: true, text: 'Average Score' }
                    }
                }
            }
        });
        
        // Engineer Performance Distribution
        const engineerData = {{ analytics_data.engineer_performance|tojson }};
        const performanceBuckets = [0, 0, 0]; // [0-5, 5-7.5, 7.5-10]
        
        engineerData.forEach(engineer => {
            const score = engineer[3] || 0;
            if (score < 5) performanceBuckets[0]++;
            else if (score < 7.5) performanceBuckets[1]++;
            else performanceBuckets[2]++;
        });
        
        new Chart(document.getElementById('engineerChart'), {
            type: 'doughnut',
            data: {
                labels: ['Needs Improvement (0-5)', 'Good (5-7.5)', 'Excellent (7.5-10)'],
                datasets: [{
                    data: performanceBuckets,
                    backgroundColor: ['#ef4444', '#f59e0b', '#10b981'],
                    borderWidth: 2,
                    borderColor: '#fff'
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { position: 'bottom' }
                }
            }
        });
    </script>
</body>
</html>""", analytics_data=analytics_data)

@app.route('/student')
def student():
    if not session.get('user_id') or session.get('is_admin'):
        return redirect('/login')
    
    user_id = session['user_id']
    
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    # Get user details
    c.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    user = c.fetchone()
    
    # Get user's assignments
    c.execute('''
        SELECT a.*, s.status as submission_status, s.total_score, s.submitted_date
        FROM assignments a
        LEFT JOIN submissions s ON a.id = s.assignment_id AND a.engineer_id = s.engineer_id
        WHERE a.engineer_id = ?
        ORDER BY a.created_date DESC
    ''', (user_id,))
    assignments = c.fetchall()
    
    conn.close()
    
    # Build assignments HTML
    assignments_html = ''
    for assignment in assignments:
        status = assignment[11] or 'pending'
        score = assignment[12] or 0
        
        if status == 'graded':
            assignments_html += f'''
            <div class="assignment-card completed">
                <div class="assignment-header">
                    <h3>✅ {assignment[2].upper()} Assessment</h3>
                    <div class="score-display">{score}/180</div>
                </div>
                <div class="assignment-meta">
                    📊 Completed on {assignment[13][:10] if assignment[13] else 'Unknown'} | 
                    🎯 Score: {score} points
                </div>
                <div class="status-badge completed">Assessment Completed</div>
            </div>'''
        elif status == 'submitted':
            assignments_html += f'''
            <div class="assignment-card submitted">
                <div class="assignment-header">
                    <h3>⏳ {assignment[2].upper()} Assessment</h3>
                    <div class="status-display">Under Review</div>
                </div>
                <div class="assignment-meta">
                    📝 Submitted on {assignment[13][:10] if assignment[13] else 'Unknown'} | 
                    ⏰ Awaiting grades
                </div>
                <div class="status-badge submitted">Under Review</div>
            </div>'''
        else:
            assignments_html += f'''
            <div class="assignment-card pending">
                <div class="assignment-header">
                    <h3>🎯 {assignment[2].upper()} Assessment</h3>
                    <div class="due-date">Due: {assignment[5][:10]}</div>
                </div>
                <div class="assignment-meta">
                    📋 18 Smart Questions | 🎖️ Max: 180 points | 
                    ⏰ Due: {assignment[5][:10]}
                </div>
                <a href="/student/test/{assignment[0]}" class="start-btn">Start Assessment</a>
            </div>'''
    
    if not assignments_html:
        assignments_html = '''
        <div class="no-assignments">
            <div class="empty-icon">📭</div>
            <h3>No Assessments Yet</h3>
            <p>Your administrator will assign assessments soon. Check back later!</p>
        </div>'''
    
    # Calculate stats
    total_assignments = len(assignments)
    completed = len([a for a in assignments if (a[11] == 'graded')])
    pending = len([a for a in assignments if not a[11] or a[11] == 'pending'])
    avg_score = sum([a[12] for a in assignments if a[12]]) / max(completed, 1) if completed > 0 else 0
    
    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
    <title>Enhanced Engineer Dashboard - {{ user[2] }}</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        :root {
            --primary: #667eea;
            --secondary: #764ba2;
            --success: #10b981;
            --warning: #f59e0b;
            --error: #ef4444;
            --surface: rgba(255, 255, 255, 0.95);
            --text-primary: #1e293b;
            --text-secondary: #64748b;
        }
        
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%);
            min-height: 100vh;
        }
        
        .header {
            background: rgba(255,255,255,0.15);
            backdrop-filter: blur(20px);
            color: white; padding: 25px 0;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
        }
        
        .header-content {
            max-width: 1200px; margin: 0 auto; padding: 0 20px;
            display: flex; justify-content: space-between; align-items: center;
        }
        
        .user-info {
            display: flex; align-items: center; gap: 15px;
        }
        
        .user-avatar {
            width: 50px; height: 50px;
            background: rgba(255,255,255,0.2);
            border-radius: 50%; display: flex; align-items: center; justify-content: center;
            font-weight: 900; font-size: 20px;
            backdrop-filter: blur(10px);
        }
        
        .welcome-text h1 {
            font-size: 24px; font-weight: 700; margin-bottom: 5px;
        }
        
        .welcome-text p {
            opacity: 0.9; font-size: 14px;
        }
        
        .nav-actions {
            display: flex; gap: 15px;
        }
        
        .nav-btn {
            background: rgba(255,255,255,0.2);
            color: white; padding: 10px 15px;
            text-decoration: none; border-radius: 8px;
            backdrop-filter: blur(10px); transition: all 0.3s ease;
            font-weight: 600; font-size: 14px;
        }
        
        .nav-btn:hover {
            background: rgba(255,255,255,0.3);
            transform: translateY(-2px);
        }
        
        .container {
            max-width: 1200px; margin: 30px auto; padding: 0 20        
        .logo::before {
            content: ''; position: absolute;
            top: 0; left: 0; right: 0; bottom: 0;
            background: linear-gradient(45deg, transparent 30%, rgba(255,255,255,0.1) 50%, transparent 70%);
            transform: translateX(-100%);
            animation: shine 3s infinite;
        }
        
        @keyframes shine {
            0% { transform: translateX(-100%); }
            50% { transform: translateX(100%); }
            100% { transform: translateX(100%); }
        }
        
        .title {
            font-size: 28px; font-weight: 700;
            background: linear-gradient(135deg, #1e293b, #475569);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            margin-bottom: 8px;
        }
        
        .subtitle {
            color: #64748b; font-size: 16px; font-weight: 500;
            margin-bottom: 35px;
        }
        
        .form-group {
            margin-bottom: 24px;
        }
        
        .form-group label {
            display: block; margin-bottom: 8px;
            color: #374151; font-weight: 600; font-size: 14px;
        }
        
        .form-input {
            width: 100%; padding: 16px 20px;
            border: 2px solid var(--border);
            border-radius: 12px; font-size: 16px;
            transition: all 0.3s ease;
            background: rgba(255, 255, 255, 0.8);
        }
        
        .form-input:focus {
            outline: none; border-color: var(--primary-color);
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
            background: white;
        }
        
        .login-btn {
            width: 100%; padding: 16px;
            background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
            color: white; border: none; border-radius: 12px;
            font-size: 16px; font-weight: 600; cursor: pointer;
            transition: all 0.3s ease; margin-bottom: 30px;
        }
        
        .login-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 25px rgba(102, 126, 234, 0.4);
        }
        
        .info-card {
            background: linear-gradient(135deg, #f8fafc, #f1f5f9);
            border: 1px solid var(--border);
            border-radius: 16px; padding: 24px; text-align: center;
        }
        
        .credentials {
            background: white; border-radius: 8px; padding: 12px;
            margin: 12px 0; border-left: 4px solid var(--primary-color);
        }
        
        .feature-highlights {
            margin-top: 15px; font-size: 12px; color: #64748b;
            line-height: 1.6;
        }
        
        .new-badge {
            background: var(--success-color); color: white;
            padding: 2px 6px; border-radius: 10px;
            font-size: 10px; font-weight: 600; margin-left: 5px;
        }
        
        @media (max-width: 480px) {
            .container { padding: 30px 20px; }
            .title { font-size: 24px; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="logo-section">
            <div class="logo">V7</div>
            <div class="title">Enhanced PD Portal</div>
            <div class="subtitle">Advanced Assessment & Analytics System</div>
        </div>
        
        <form method="POST">
            <div class="form-group">
                <label>Username</label>
                <input type="text" name="username" class="form-input" 
                       placeholder="Enter your username" required autocomplete="username">
            </div>
            <div class="form-group">
                <label>Password</label>
                <input type="password" name="password" class="form-input" 
                       placeholder="Enter your password" required autocomplete="current-password">
            </div>
            <button type="submit" class="login-btn">Access Enhanced Portal</button>
        </form>
        
        <div class="info-card">
            <div style="font-weight: 700; margin-bottom: 16px;">🔐 Demo Credentials</div>
            <div class="credentials">
                <strong>Engineers:</strong> eng001 through eng018<br>
                <strong>Password:</strong> password123<br>
                <strong>Admin:</strong> admin / Vibhuaya@3006
            </div>
            <div class="feature-highlights">
                <strong>🚀 New Features:</strong><br>
                Smart Question Generation <span class="new-badge">NEW</span><br>
                Enhanced AI Scoring <span class="new-badge">NEW</span><br>
                Performance Analytics <span class="new-badge">NEW</span><br>
                Mobile-Responsive Design <span class="new-badge">NEW</span>
            </div>
        </div>
    </div>
</body>
</html>""")

@app.route('/logout')
def logout():
    user_id = session.get('user_id')
    if user_id:
        DatabaseManager.log_analytics('logout', user_id)
    
    session.clear()
    return redirect('/login')

@app.route('/admin')
def admin():
    if not session.get('is_admin'):
        return redirect('/login')
    
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    # Get comprehensive statistics
    c.execute('SELECT COUNT(*) FROM users WHERE is_admin = 0')
    total_engineers = c.fetchone()[0]
    
    c.execute('SELECT COUNT(*) FROM assignments')
    total_assignments = c.fetchone()[0]
    
    c.execute('SELECT COUNT(*) FROM submissions WHERE status = "submitted"')
    pending_reviews = c.fetchone()[0]
    
    c.execute('SELECT COUNT(*) FROM submissions WHERE status = "graded"')
    completed_reviews = c.fetchone()[0]
    
    # Get engineers for dropdown
    c.execute('SELECT * FROM users WHERE is_admin = 0 ORDER BY display_name')
    engineers = c.fetchall()
    
    # Get recent activity
    c.execute('''
        SELECT s.*, a.topic, u.display_name, a.created_date as assignment_date
        FROM submissions s
        JOIN assignments a ON s.assignment_id = a.id
        JOIN users u ON s.engineer_id = u.id
        WHERE s.status = "submitted"
        ORDER BY s.submitted_date DESC
        LIMIT 10
    ''')
    pending_submissions = c.fetchall()
    
    # Get performance analytics
    c.execute('''
        SELECT 
            topic,
            COUNT(*) as count,
            AVG(CAST(total_score as FLOAT)) as avg_score,
            MAX(CAST(total_score as FLOAT)) as max_score,
            MIN(CAST(total_score as FLOAT)) as min_score
        FROM submissions s
        JOIN assignments a ON s.assignment_id = a.id
        WHERE s.status = "graded" AND s.total_score > 0
        GROUP BY topic
    ''')
    topic_stats = c.fetchall()
    
    conn.close()
    
    # Build engineer options
    eng_options = ''
    for eng in engineers:
        exp_years = eng[6] if eng[6] else 3
        eng_options += f'<option value="{eng[0]}" data-exp="{exp_years}">{eng[2]} ({exp_years}y exp)</option>'
    
    # Build pending submissions HTML
    pending_html = ''
    for sub in pending_submissions:
        time_ago = _time_ago(sub[4])
        pending_html += f'''
        <div class="submission-card">
            <div class="submission-header">
                <h4>{sub[11]} - {sub[10].upper()}</h4>
                <span class="time-badge">{time_ago}</span>
            </div>
            <div class="submission-meta">
                📝 {len(json.loads(sub[3]))} answers | 🎯 Auto-scored | ⏰ {sub[4][:16]}
            </div>
            <div class="submission-actions">
                <a href="/admin/review/{sub[1]}" class="review-btn">Review & Grade</a>
            </div>
        </div>'''
    
    if not pending_html:
        pending_html = '''
        <div class="no-submissions">
            <div class="empty-icon">📭</div>
            <h3>All Caught Up!</h3>
            <p>No pending submissions to review. Great work!</p>
        </div>'''
    
    # Build analytics charts data
    analytics_data = {
        "topic_stats": [{"topic": stat[0], "count": stat[1], "avg_score": round(stat[2], 1)} for stat in topic_stats],
        "total_engineers": total_engineers,
        "completion_rate": round((completed_reviews / max(total_assignments, 1)) * 100, 1)
    }
    
    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
    <title>Enhanced Admin Dashboard - Vibhuayu</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        :root {
            --primary: #667eea;
            --secondary: #764ba2;
            --success: #10b981;
            --warning: #f59e0b;
            --error: #ef4444;
            --bg-dark: #0f172a;
            --bg-light: #1e293b;
            --surface: #ffffff;
            --text-primary: #1e293b;
            --text-secondary: #64748b;
            --border: #e2e8f0;
        }
        
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, var(--bg-dark) 0%, var(--bg-light) 100%);
            min-height: 100vh; color: var(--text-primary);
        }
        
        .header {
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            padding: 20px 0; box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
            position: relative; overflow: hidden;
        }
        
        .header::before {
            content: ''; position: absolute;
            top: 0; left: 0; right: 0; bottom: 0;
            background: linear-gradient(45deg, transparent 30%, rgba(255,255,255,0.1) 50%, transparent 70%);
            transform: translateX(-100%);
            animation: headerShine 4s infinite;
        }
        
        @keyframes headerShine {
            0% { transform: translateX(-100%); }
            50% { transform: translateX(100%); }
            100% { transform: translateX(100%); }
        }
        
        .header-content {
            max-width: 1400px; margin: 0 auto; padding: 0 20px;
            display: flex; align-items: center; justify-content: space-between;
            position: relative; z-index: 2;
        }
        
        .header-title {
            display: flex; align-items: center; gap: 15px;
        }
        
        .header-logo {
            width: 50px; height: 50px;
            background: rgba(255, 255, 255, 0.15);
            border-radius: 12px; display: flex; align-items: center; justify-content: center;
            font-weight: 900; color: white; font-size: 20px;
            backdrop-filter: blur(10px);
        }
        
        .header h1 {
            color: white; font-size: 28px; font-weight: 700;
            text-shadow: 0 2px 10px rgba(0,0,0,0.3);
        }
        
        .nav-menu {
            display: flex; gap: 15px; align-items: center;
        }
        
        .nav-btn {
            background: rgba(255, 255, 255, 0.15); color: white;
            padding: 10px 15px; text-decoration: none; border-radius: 8px;
            backdrop-filter: blur(10px); transition: all 0.3s ease;
            font-weight: 600; font-size: 14px;
        }
        
        .nav-btn:hover {
            background: rgba(255, 255, 255, 0.25);
            transform: translateY(-2px);
        }
        
        .container {
            max-width: 1400px; margin: 30px auto; padding: 0 20px;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 25px; margin-bottom: 40px;
        }
        
        .stat-card {
            background: linear-gradient(135deg, var(--surface) 0%, #f8fafc 100%);
            padding: 30px; border-radius: 20px; text-align: center;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.2);
            transition: transform 0.3s ease;
        }
        
        .stat-card:hover { transform: translateY(-5px); }
        
        .stat-number {
            font-size: 42px; font-weight: 800;
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            margin-bottom: 8px; line-height: 1;
        }
        
        .stat-label {
            color: var(--text-secondary); font-weight: 600;
            font-size: 14px; text-transform: uppercase; letter-spacing: 1px;
        }
        
        .stat-trend {
            margin-top: 10px; font-size: 12px; font-weight: 600;
        }
        
        .trend-up { color: var(--success); }
        .trend-down { color: var(--error); }
        
        .main-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
        }
        
        .card {
            background: linear-gradient(135deg, var(--surface) 0%, #f8fafc 100%);
            border-radius: 20px; padding: 30px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.2);
        }
        
        .card h2 {
            color: var(--text-primary); margin-bottom: 25px;
            font-size: 24px; font-weight: 700;
            display: flex; align-items: center; gap: 10px;
        }
        
        .form-row {
            display: grid;
            grid-template-columns: 1fr 1fr auto;
            gap: 15px; align-items: end;
        }
        
        .form-group {
            display: flex; flex-direction: column;
        }
        
        .form-group label {
            margin-bottom: 8px; font-weight: 600;
            color: var(--text-primary); font-size: 14px;
        }
        
        select, button {
            padding: 14px 18px; border: 2px solid var(--border);
            border-radius: 12px; font-size: 16px;
            transition: all 0.3s ease; background: white;
            font-family: inherit;
        }
        
        select:focus {
            outline: none; border-color: var(--primary);
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }
        
        .btn-primary {
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            color: white; border: none; cursor: pointer;
            font-weight: 600; min-width: 140px;
        }
        
        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 25px rgba(102, 126, 234, 0.4);
        }
        
        .submission-card {
            background: linear-gradient(135deg, #f8fafc, #f1f5f9);
            padding: 20px; margin: 15px 0; border-radius: 16px;
            border-left: 4px solid var(--warning);
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.05);
            transition: all 0.3s ease;
        }
        
        .submission-card:hover {
            transform: translateX(5px);
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);
        }
        
        .submission-header {
            display: flex; justify-content: space-between;
            align-items: center; margin-bottom: 10px;
        }
        
        .submission-header h4 {
            color: var(--text-primary); margin: 0; font-size: 16px;
        }
        
        .time-badge {
            background: var(--warning); color: white;
            padding: 4px 12px; border-radius: 20px;
            font-size: 12px; font-weight: 600;
        }
        
        .submission-meta {
            color: var(--text-secondary); font-size: 14px;
            margin-bottom: 15px;
        }
        
        .submission-actions {
            display: flex; gap: 10px;
        }
        
        .review-btn {
            padding: 8px 16px; text-decoration: none;
            border-radius: 8px; font-weight: 600;
            font-size: 14px; transition: all 0.3s ease;
            background: linear-gradient(135deg, var(--success), #059669);
            color: white;
        }
        
        .review-btn:hover {
            transform: translateY(-2px);
        }
        
        .no-submissions {
            text-align: center; padding: 60px 20px;
            color: var(--text-secondary);
        }
        
        .empty-icon {
            font-size: 48px; margin-bottom: 20px;
        }
        
        .analytics-preview {
            background: linear-gradient(135deg, #f0f9ff, #e0f2fe);
            border-radius: 12px; padding: 20px;
            margin-top: 20px;
        }
        
        .analytics-item {
            display: flex; justify-content: space-between;
            align-items: center; padding: 10px 0;
            border-bottom: 1px solid rgba(102, 126, 234, 0.1);
        }
        
        .analytics-item:last-child { border-bottom: none; }
        
        @media (max-width: 768px) {
            .main-grid { grid-template-columns: 1fr; }
            .form-row { grid-template-columns: 1fr; gap: 15px; }
            .stats-grid { grid-template-columns: repeat(2, 1fr); }
            .header-content { flex-direction: column; gap: 15px; text-align: center; }
            .nav-menu { flex-wrap: wrap; justify-content: center; }
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="header-content">
            <div class="header-title">
                <div class="header-logo">V7</div>
                <h1>🚀 Enhanced Admin Dashboard</h1>
            </div>
            <div class="nav-menu">
                <a href="/admin/analytics" class="nav-btn">📊 Analytics</a>
                <a href="/logout" class="nav-btn">🚪 Logout</a>
            </div>
        </div>
    </div>
    
    <div class="container">
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-number">{{ total_engineers }}</div>
                <div class="stat-label">Engineers</div>
                <div class="stat-trend trend-up">↗ Active Users</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ total_assignments }}</div>
                <div class="stat-label">Assessments</div>
                <div class="stat-trend trend-up">📈 Total Created</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ pending_reviews }}</div>
                <div class="stat-label">Pending Reviews</div>
                <div class="stat-trend trend-up">⏳ Need Attention</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ analytics_data.completion_rate }}%</div>
                <div class="stat-label">Completion Rate</div>
                <div class="stat-trend trend-up">✅ Success Rate</div>
            </div>
        </div>
        
        <div class="main-grid">
            <div class="card">
                <h2>🎯 Create Smart Assessment</h2>
                <form method="POST" action="/admin/create">
                    <div class="form-row">
                        <div class="form-group">
                            <label>Select Engineer</label>
                            <select name="engineer_id" required id="engineerSelect">
                                <option value="">Choose engineer...</option>
                                {{ eng_options }}
                            </select>
                        </div>
                        <div class="form-group">
                            <label>Assessment Topic</label>
                            <select name="topic" required>
                                <option value="">Select topic...</option>
                                <option value="sta">🕒 STA (Static Timing Analysis)</option>
                                <option value="cts">🌳 CTS (Clock Tree Synthesis)</option>
                                <option value="signoff">✅ Signoff Checks & Verification</option>
                            </select>
                        </div>
                        <button type="submit" class="btn-primary">Create Assessment</button>
                    </div>
                    <div class="analytics-preview">
                        <div class="analytics-item">
                            <span>📝 Questions Generated:</span>
                            <strong>18 (Adaptive Difficulty)</strong>
                        </div>
                        <div class="analytics-item">
                            <span>🤖 AI Scoring:</span>
                            <strong>Enabled</strong>
                        </div>
                        <div class="analytics-item">
                            <span>📊 Analytics Tracking:</span>
                            <strong>Full Coverage</strong>
                        </div>
                    </div>
                </form>
            </div>
            
            <div class="card">
                <h2>📋 Pending Reviews ({{ pending_reviews }})</h2>
                <div style="max-height: 400px; overflow-y: auto;">
                    {{ pending_html|safe }}
                </div>
            </div>
        </div>
        
        {% if analytics_data.topic_stats %}
        <div class="card" style="margin-top: 30px;">
            <h2>📈 Performance Analytics</h2>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px;">
                {% for stat in analytics_data.topic_stats %}
                <div class="analytics-item">
                    <div>
                        <span style="background: var(--primary); color: white; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; text-transform: uppercase;">{{ stat.topic }}</span>
                        <div style="margin-top: 8px;">
                            <strong>{{ stat.count }}</strong> submissions<br>
                            <strong>{{ stat.avg_score }}</strong> avg score
                        </div>
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>
        {% endif %}
    </div>
    
    <script>
        // Enhanced interactivity
        document.getElementById('engineerSelect').addEventListener('change', function() {
            const selectedOption = this.selectedOptions[0];
            const experience = selectedOption.getAttribute('data-exp');
            if (experience) {
                console.log(`Selected engineer with ${experience} years experience`);
            }
        });
        
        // Auto-refresh pending count every 30 seconds
        setInterval(() => {
            fetch('/admin/stats')
                .then(response => response.json())
                .then(data => {
                    console.log('Stats updated');
                })
                .catch(err => console.log('Stats update failed'));
        }, 30000);
    </script>
</body>
</html>""", 
    total_engineers=total_engineers,
    total_assignments=total_assignments,
    pending_reviews=pending_reviews,
    completed_reviews=completed_reviews,
    eng_options=eng_options,
    pending_html=pending_html,
    analytics_data=analytics_data
    )

@app.route('/admin/create', methods=['POST'])
def admin_create():
    if not session.get('is_admin'):
        return redirect('/login')
    
    engineer_id = request.form.get('engineer_id')
    topic = request.form.get('topic')
    
    if not engineer_id or not topic:
        return redirect('/admin')
    
    # Get engineer experience for adaptive questions
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('SELECT experience FROM users WHERE id = ?', (engineer_id,))
    engineer = c.fetchone()
    experience = engineer[0] if engineer else 3
    
    # Generate smart questions
    questions = question_generator.generate_smart_questions(topic, 18, experience)
    
    # Create assignment
    assignment_id = f"PD_{topic}_{engineer_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    due_date = (datetime.now() + timedelta(days=7)).isoformat()
    
    c.execute("""
        INSERT INTO assignments (id, engineer_id, topic, questions, created_date, due_date, created_by)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (assignment_id, engineer_id, topic, json.dumps(questions), 
          datetime.now().isoformat(), due_date, session['user_id']))
    
    conn.commit()
    conn.close()
    
    # Log analytics
    DatabaseManager.log_analytics('assignment_created', session['user_id'], {
        'assignment_id': assignment_id,
        'topic': topic,
        'engineer_id': engineer_id
    })
    
    return redirect('/admin')

@app.route('/admin/review/<assignment_id>', methods=['GET', 'POST'])
def admin_review(assignment_id):
    if not session.get('is_admin'):
        return redirect('/login')
    
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    # Get submission details
    c.execute('''
        SELECT s.*, a.topic, a.questions, u.display_name
        FROM submissions s
        JOIN assignments a ON s.assignment_id = a.id
        JOIN users u ON s.engineer_id = u.id
        WHERE s.assignment_id = ?
    ''', (assignment_id,))
    submission = c.fetchone()
    
    if not submission:
        conn.close()
        return redirect('/admin')
    
    # Process submission data
    answers = json.loads(submission[3])
    questions = json.loads(submission[12])
    auto_scores = json.loads(submission[6]) if submission[6] else {}
    
    # Handle grading submission
    if request.method == 'POST':
        manual_scores = {}
        feedback_notes = {}
        total_score = 0
        
        for i in range(len(questions)):
            manual_score = request.form.get(f'score_{i}', 0)
            feedback_note = request.form.get(f'feedback_{i}', '')
            try:
                score = float(manual_score)
                manual_scores[str(i)] = score
                feedback_notes[str(i)] = feedback_note
                total_score += score
            except:
                manual_scores[str(i)] = 0
        
        # Update submission with grades
        c.execute('''
            UPDATE submissions 
            SET manual_scores = ?, feedback = ?, total_score = ?, 
                status = 'graded', graded_by = ?, graded_date = ?
            WHERE assignment_id = ?
        ''', (json.dumps(manual_scores), json.dumps(feedback_notes), 
              total_score, session['user_id'], datetime.now().isoformat(), assignment_id))
        conn.commit()
        conn.close()
        
        # Log analytics
        DatabaseManager.log_analytics('submission_graded', session['user_id'], {
            'assignment_id': assignment_id,
            'total_score': total_score,
            'engineer_id': submission[2]
        })
        
        return redirect('/admin')
    
    conn.close()
    
    # Build review interface
    questions_html = ''
    for i, question in enumerate(questions):
        answer = answers.get(str(i), 'No answer provided')
        auto_score_data = auto_scores.get(str(i), {})
        suggested_score = auto_score_data.get('score', 0)
        
        # Enhanced scoring analysis
        if answer and answer != 'No answer provided':
            score_analysis = scoring_system.analyze_answer_comprehensive(question, answer, submission[11])
            suggested_score = score_analysis['score']
            breakdown = score_analysis['breakdown']
            suggestions = score_analysis['suggestions']
        else:
            breakdown = {"technical": 0, "depth": 0, "methodology": 0, "clarity": 0}
            suggestions = ["Answer not provided"]
        
        color = "#10b981" if suggested_score >= 7 else "#f59e0b# Enhanced PD Assessment System - Complete app.py for Railway
import os
import hashlib
import json
import random
import sqlite3
from datetime import datetime, timedelta
from threading import Lock
from flask import Flask, request, redirect, session, jsonify, render_template_string
import re

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'pd-secret-key-enhanced')

# Database setup
DATABASE = 'enhanced_assessments.db'
db_lock = Lock()

class DatabaseManager:
    @staticmethod
    def init_db():
        """Initialize SQLite database with enhanced schema"""
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        
        # Users table
        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE,
                display_name TEXT,
                email TEXT,
                password TEXT,
                is_admin BOOLEAN DEFAULT 0,
                experience INTEGER DEFAULT 3,
                department TEXT,
                created_date TEXT,
                last_login TEXT,
                theme TEXT DEFAULT 'light'
            )
        """)
        
        # Assignments table
        c.execute("""
            CREATE TABLE IF NOT EXISTS assignments (
                id TEXT PRIMARY KEY,
                engineer_id TEXT,
                topic TEXT,
                questions TEXT,
                created_date TEXT,
                due_date TEXT,
                status TEXT DEFAULT 'pending',
                difficulty_level INTEGER DEFAULT 1,
                max_points INTEGER DEFAULT 180,
                created_by TEXT,
                FOREIGN KEY (engineer_id) REFERENCES users (id)
            )
        """)
        
        # Submissions table (enhanced)
        c.execute("""
            CREATE TABLE IF NOT EXISTS submissions (
                id TEXT PRIMARY KEY,
                assignment_id TEXT,
                engineer_id TEXT,
                answers TEXT,
                submitted_date TEXT,
                status TEXT DEFAULT 'submitted',
                auto_scores TEXT,
                manual_scores TEXT,
                feedback TEXT,
                total_score INTEGER DEFAULT 0,
                graded_by TEXT,
                graded_date TEXT,
                time_spent INTEGER DEFAULT 0,
                FOREIGN KEY (assignment_id) REFERENCES assignments (id),
                FOREIGN KEY (engineer_id) REFERENCES users (id)
            )
        """)
        
        # Analytics table
        c.execute("""
            CREATE TABLE IF NOT EXISTS analytics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT,
                user_id TEXT,
                data TEXT,
                timestamp TEXT
            )
        """)
        
        conn.commit()
        conn.close()
    
    @staticmethod
    def log_analytics(event_type, user_id, data=None):
        """Log analytics events"""
        with db_lock:
            conn = sqlite3.connect(DATABASE)
            c = conn.cursor()
            c.execute("""
                INSERT INTO analytics (event_type, user_id, data, timestamp)
                VALUES (?, ?, ?, ?)
            """, (event_type, user_id, json.dumps(data) if data else None, datetime.now().isoformat()))
            conn.commit()
            conn.close()

# Enhanced Question Generation with Smart AI
class SmartQuestionGenerator:
    def __init__(self):
        self.question_templates = {
            "sta": [
                {
                    "template": "Your design has {violation_type} violations of {violation_amount}ps on {num_paths} critical paths. The design is running at {frequency}MHz. Analyze the root causes and propose {num_solutions} specific solutions with expected improvement estimates.",
                    "difficulty": 3,
                    "parameters": {
                        "violation_type": ["setup", "hold", "max_transition"],
                        "violation_amount": [20, 50, 100, 150, 200],
                        "num_paths": [10, 25, 50, 100, 200],
                        "frequency": [500, 800, 1000, 1500, 2000],
                        "num_solutions": [3, 4, 5]
                    }
                },
                {
                    "template": "Explain the concept of {concept} in static timing analysis. How does it impact {impact_area} and what are the industry-standard approaches to handle it in {technology_node} designs?",
                    "difficulty": 2,
                    "parameters": {
                        "concept": ["clock jitter", "OCV", "useful skew", "clock latency", "timing corners"],
                        "impact_area": ["setup timing", "hold timing", "power consumption", "area optimization"],
                        "technology_node": ["7nm", "5nm", "3nm", "advanced nodes"]
                    }
                },
                {
                    "template": "You're analyzing a {design_type} with {num_domains} clock domains running at different frequencies. Describe your approach to handle clock domain crossings and ensure timing closure across all interfaces.",
                    "difficulty": 4,
                    "parameters": {
                        "design_type": ["SoC", "CPU", "GPU", "AI accelerator"],
                        "num_domains": [3, 4, 5, 6]
                    }
                }
            ],
            "cts": [
                {
                    "template": "Design a clock tree for a {design_size} design with {num_flops} flip-flops distributed across {die_size}. The target skew is {target_skew}ps and you have {buffer_types} buffer types available. Explain your tree topology choice and optimization strategy.",
                    "difficulty": 3,
                    "parameters": {
                        "design_size": ["large-scale", "medium-scale", "complex"],
                        "num_flops": [10000, 25000, 50000, 100000],
                        "die_size": ["5mm x 5mm", "10mm x 10mm", "15mm x 15mm"],
                        "target_skew": [25, 50, 75, 100],
                        "buffer_types": [3, 4, 5, 6]
                    }
                },
                {
                    "template": "Your clock tree has {power_consumption}mW power consumption, which is {percentage}% of total chip power. Propose {num_techniques} specific techniques to reduce clock power while maintaining {skew_constraint}ps skew constraint.",
                    "difficulty": 4,
                    "parameters": {
                        "power_consumption": [50, 100, 150, 200],
                        "percentage": [15, 20, 25, 30, 35],
                        "num_techniques": [3, 4, 5],
                        "skew_constraint": [30, 50, 75]
                    }
                }
            ],
            "signoff": [
                {
                    "template": "Your design failed {check_type} with {num_violations} violations. The violations are distributed as: {violation_dist}. Create a systematic debugging and resolution plan with priority ordering and estimated effort.",
                    "difficulty": 3,
                    "parameters": {
                        "check_type": ["DRC", "LVS", "Antenna", "Metal Density"],
                        "num_violations": [50, 100, 200, 500],
                        "violation_dist": ["70% spacing, 20% width, 10% via", "50% density, 30% spacing, 20% antenna"]
                    }
                },
                {
                    "template": "Perform signoff analysis for a {design_type} in {technology} process. The design has {power_domains} power domains and {io_count} I/Os. List all required signoff checks and create a verification plan with timeline.",
                    "difficulty": 4,
                    "parameters": {
                        "design_type": ["automotive SoC", "mobile processor", "IoT chip", "high-performance CPU"],
                        "technology": ["7nm FinFET", "5nm", "3nm GAA"],
                        "power_domains": [2, 3, 4, 5],
                        "io_count": [100, 200, 500, 1000]
                    }
                }
            ]
        }
    
    def generate_smart_questions(self, topic, num_questions=18, engineer_exp=3):
        """Generate questions with adaptive difficulty"""
        templates = self.question_templates.get(topic, [])
        if not templates:
            return self._fallback_questions(topic)
        
        questions = []
        difficulty_distribution = self._get_difficulty_distribution(engineer_exp, num_questions)
        
        for target_difficulty in difficulty_distribution:
            suitable_templates = [t for t in templates if abs(t["difficulty"] - target_difficulty) <= 1]
            if not suitable_templates:
                suitable_templates = templates
            
            template = random.choice(suitable_templates)
            question = self._generate_from_template(template)
            questions.append(question)
        
        return questions[:num_questions]
    
    def _get_difficulty_distribution(self, engineer_exp, num_questions):
        """Create difficulty distribution based on experience"""
        if engineer_exp <= 2:
            easy_count = int(num_questions * 0.6)
            medium_count = int(num_questions * 0.3)
            hard_count = num_questions - easy_count - medium_count
            return [2] * easy_count + [3] * medium_count + [4] * hard_count
        elif engineer_exp <= 4:
            easy_count = int(num_questions * 0.3)
            medium_count = int(num_questions * 0.5)
            hard_count = num_questions - easy_count - medium_count
            return [2] * easy_count + [3] * medium_count + [4] * hard_count
        else:
            easy_count = int(num_questions * 0.2)
            medium_count = int(num_questions * 0.4)
            hard_count = num_questions - easy_count - medium_count
            return [2] * easy_count + [3] * medium_count + [4] * hard_count
    
    def _generate_from_template(self, template_data):
        """Generate question from template with random parameters"""
        template = template_data["template"]
        params = template_data["parameters"]
        
        generated_params = {}
        for param, options in params.items():
            generated_params[param] = random.choice(options)
        
        try:
            return template.format(**generated_params)
        except KeyError:
            return template
    
    def _fallback_questions(self, topic):
        """Fallback to static questions if smart generation fails"""
        fallback = {
            "sta": [
                "What is Static Timing Analysis and why is it critical in modern chip design?",
                "Explain setup and hold time violations. How do you debug and fix them?",
                "What is clock skew and how does it impact timing closure?",
                "Describe the concept of timing corners and their importance in analysis.",
                "How do you handle timing analysis for multiple clock domains?",
                "What are timing exceptions and when would you use false paths?",
                "Explain the difference between ideal clock and propagated clock analysis.",
                "What is clock jitter and how do you account for it in timing calculations?",
                "How do you analyze timing for memory interfaces and what makes them special?",
                "What is OCV (On-Chip Variation) and why do you add OCV margins in STA?",
                "Explain multicycle paths and give an example where you would use them.",
                "How do you handle timing analysis for generated clocks and clock dividers?",
                "What is clock domain crossing (CDC) and what timing checks are needed?",
                "Describe timing analysis for high-speed interfaces and their challenges.",
                "What reports do you check for timing signoff and why are they important?",
                "How do you ensure timing correlation between STA tools and silicon?",
                "What is useful skew and how can it help with timing closure?",
                "Explain timing optimization techniques for low-power designs."
            ],
            "cts": [
                "What is Clock Tree Synthesis and what are its main objectives?",
                "Explain different clock tree topologies and when to use each.",
                "How do you optimize clock trees for power consumption?",
                "What is useful skew and how can it help timing closure?",
                "Describe challenges in CTS for high-frequency designs.",
                "What is clock skew and what causes it in clock trees?",
                "How do you handle clock gating cells in clock tree synthesis?",
                "Explain the concept of clock insertion delay and how to minimize it.",
                "What are the trade-offs between H-tree and balanced tree topologies?",
                "How do you handle multiple clock domains in CTS?",
                "What is clock mesh and when would you choose it over tree topology?",
                "Describe clock tree optimization for process variation and yield.",
                "How do you build clock trees for multi-voltage designs?",
                "What is the typical CTS flow and when does it happen in the design cycle?",
                "How do you verify clock tree quality after synthesis?",
                "What are the challenges of clock tree synthesis in advanced nodes?",
                "Explain clock tree balancing and why it's important.",
                "How do you handle clock tree synthesis for low-power designs?"
            ],
            "signoff": [
                "What are the main signoff checks required before tape-out?",
                "Explain DRC violations and systematic approaches to fix them.",
                "What is LVS and how do you debug LVS mismatches?",
                "Describe IR drop analysis and mitigation techniques.",
                "How do you perform timing signoff for multi-corner analysis?",
                "What is antenna checking and why can violations damage your chip?",
                "Explain metal density rules and their impact on manufacturing.",
                "What is electromigration and how do you prevent EM violations?",
                "How do you perform signal integrity analysis during signoff?",
                "What is formal verification and how does it differ from simulation?",
                "Describe the signoff flow for advanced technology nodes.",
                "How do you coordinate signoff across different design teams?",
                "What additional checks are needed for multi-voltage designs?",
                "Explain thermal analysis and its importance in signoff.",
                "What is yield analysis and how do you optimize for manufacturing yield?",
                "How do you validate power delivery networks during signoff?",
                "What are the challenges of signoff in 7nm and below technologies?",
                "Describe the handoff process between design and manufacturing teams."
            ]
        }
        
        base_questions = fallback.get(topic, fallback["sta"])
        extended = []
        for i in range(18):
            base_q = base_questions[i % len(base_questions)]
            if i >= len(base_questions):
                extended.append(f"Advanced: {base_q}")
            else:
                extended.append(base_q)
        return extended

# Enhanced Scoring System
class EnhancedScoringSystem:
    def __init__(self):
        self.scoring_rubrics = {
            "sta": {
                "technical_terms": ["setup", "hold", "slack", "skew", "jitter", "corner", "violation", "closure"],
                "advanced_terms": ["ocv", "cppr", "useful skew", "clock latency", "propagated", "ideal"],
                "methodology_terms": ["debug", "optimize", "analyze", "systematic", "root cause"],
                "weights": {"technical": 0.4, "depth": 0.3, "methodology": 0.2, "clarity": 0.1}
            },
            "cts": {
                "technical_terms": ["clock tree", "skew", "insertion delay", "buffer", "topology", "synthesis"],
                "advanced_terms": ["h-tree", "mesh", "useful skew", "gating", "power optimization"],
                "methodology_terms": ["balance", "optimize", "strategy", "approach", "technique"],
                "weights": {"technical": 0.4, "depth": 0.3, "methodology": 0.2, "clarity": 0.1}
            },
            "signoff": {
                "technical_terms": ["drc", "lvs", "antenna", "density", "ir drop", "em", "signoff"],
                "advanced_terms": ["formal verification", "multi-corner", "yield analysis", "si analysis"],
                "methodology_terms": ["debug", "systematic", "flow", "process", "validation"],
                "weights": {"technical": 0.4, "depth": 0.3, "methodology": 0.2, "clarity": 0.1}
            }
        }
    
    def analyze_answer_comprehensive(self, question, answer, topic):
        """Comprehensive answer analysis with detailed feedback"""
        if not answer or len(answer.strip()) < 20:
            return {
                "score": 0,
                "breakdown": {"technical": 0, "depth": 0, "methodology": 0, "clarity": 0},
                "feedback": "Answer too short or empty",
                "suggestions": ["Provide more detailed technical explanation", "Include specific examples", "Explain methodology"]
            }
        
        rubric = self.scoring_rubrics.get(topic, self.scoring_rubrics["sta"])
        answer_lower = answer.lower()
        word_count = len(answer.split())
        
        # Technical accuracy score
        technical_score = self._score_technical_content(answer_lower, rubric)
        
        # Depth and detail score
        depth_score = self._score_depth(answer, word_count)
        
        # Methodology score
        methodology_score = self._score_methodology(answer_lower, rubric)
        
        # Clarity and structure score
        clarity_score = self._score_clarity(answer)
        
        # Weighted final score
        weights = rubric["weights"]
        final_score = (
            technical_score * weights["technical"] +
            depth_score * weights["depth"] +
            methodology_score * weights["methodology"] +
            clarity_score * weights["clarity"]
        ) * 10
        
        # Generate feedback and suggestions
        feedback, suggestions = self._generate_feedback(
            technical_score, depth_score, methodology_score, clarity_score, word_count
        )
        
        return {
            "score": round(final_score, 1),
            "breakdown": {
                "technical": round(technical_score * 10, 1),
                "depth": round(depth_score * 10, 1),
                "methodology": round(methodology_score * 10, 1),
                "clarity": round(clarity_score * 10, 1)
            },
            "feedback": feedback,
            "suggestions": suggestions,
            "word_count": word_count
        }
    
    def _score_technical_content(self, answer_lower, rubric):
        tech_terms = sum(1 for term in rubric["technical_terms"] if term in answer_lower)
        advanced_terms = sum(1 for term in rubric["advanced_terms"] if term in answer_lower)
        
        tech_score = min(tech_terms / 3, 1.0)
        advanced_score = min(advanced_terms / 2, 0.5)
        
        return min(tech_score + advanced_score, 1.0)
    
    def _score_depth(self, answer, word_count):
        word_score = min(word_count / 100, 0.7)
        
        has_examples = any(marker in answer.lower() for marker in ['example', 'for instance', 'such as'])
        has_numbers = bool(re.search(r'\d+', answer))
        has_comparisons = any(marker in answer.lower() for marker in ['compare', 'versus', 'vs', 'better', 'worse'])
        
        structure_score = (has_examples * 0.1) + (has_numbers * 0.1) + (has_comparisons * 0.1)
        
        return min(word_score + structure_score, 1.0)
    
    def _score_methodology(self, answer_lower, rubric):
        method_terms = sum(1 for term in rubric["methodology_terms"] if term in answer_lower)
        
        has_steps = any(marker in answer_lower for marker in ['step', 'first', 'second', 'then', 'next', 'finally'])
        has_process = any(marker in answer_lower for marker in ['process', 'flow', 'procedure', 'approach'])
        
        method_score = min(method_terms / 2, 0.7)
        process_score = (has_steps * 0.15) + (has_process * 0.15)
        
        return min(method_score + process_score, 1.0)
    
    def _score_clarity(self, answer):
        sentences = answer.split('.')
        avg_sentence_length = sum(len(s.split()) for s in sentences) / max(len(sentences), 1)
        
        length_score = 1.0 - abs(avg_sentence_length - 17.5) / 17.5
        length_score = max(0, min(length_score, 1.0))
        
        has_organization = any(marker in answer.lower() for marker in [':', '-', '1.', '2.', 'bullet'])
        org_score = 0.3 if has_organization else 0
        
        return min(length_score * 0.7 + org_score, 1.0)
    
    def _generate_feedback(self, tech_score, depth_score, method_score, clarity_score, word_count):
        feedback_parts = []
        suggestions = []
        
        if tech_score >= 0.8:
            feedback_parts.append("Strong technical knowledge demonstrated")
        elif tech_score >= 0.6:
            feedback_parts.append("Good technical understanding shown")
            suggestions.append("Include more specific technical terminology")
        else:
            feedback_parts.append("Limited technical content")
            suggestions.append("Use more industry-specific technical terms")
        
        if depth_score >= 0.8:
            feedback_parts.append("comprehensive analysis provided")
        elif depth_score >= 0.6:
            feedback_parts.append("adequate detail level")
            suggestions.append("Provide more detailed explanations and examples")
        else:
            feedback_parts.append("needs more depth")
            suggestions.append("Expand with specific examples and quantitative details")
        
        if method_score >= 0.7:
            feedback_parts.append("clear methodology described")
        else:
            feedback_parts.append("methodology could be clearer")
            suggestions.append("Describe step-by-step approach or process")
        
        if word_count < 50:
            suggestions.append("Increase answer length for better coverage")
        elif word_count > 300:
            suggestions.append("Consider more concise explanations")
        
        feedback = ", ".join(feedback_parts).capitalize() + f" ({word_count} words)"
        
        return feedback, suggestions

# Initialize components
DatabaseManager.init_db()
question_generator = SmartQuestionGenerator()
scoring_system = EnhancedScoringSystem()

# User authentication functions
def hash_pass(pwd):
    return hashlib.sha256(pwd.encode()).hexdigest()

def check_pass(hashed, pwd):
    return hashed == hashlib.sha256(pwd.encode()).hexdigest()

def init_data():
    """Initialize demo data"""
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    # Check if admin exists
    c.execute('SELECT id FROM users WHERE id = ?', ('admin',))
    if not c.fetchone():
        # Create admin
        c.execute("""
            INSERT INTO users (id, username, display_name, email, password, is_admin, experience, created_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, ('admin', 'admin', 'System Administrator', 'admin@vibhuayu.com', 
              hash_pass('Vibhuaya@3006'), 1, 5, datetime.now().isoformat()))
        
        # Create 18 engineers
        engineer_data = [
            ('eng001', 'Kranthi', 'kranthi@vibhuayu.com', 3),
            ('eng002', 'Neela', 'neela@vibhuayu.com', 4),
            ('eng003', 'Bhanu', 'bhanu@vibhuayu.com', 2),
            ('eng004', 'Lokeshwari', 'lokeshwari@vibhuayu.com', 5),
            ('eng005', 'Nagesh', 'nagesh@vibhuayu.com', 3),
            ('eng006', 'VJ', 'vj@vibhuayu.com', 4),
            ('eng007', 'Pravalika', 'pravalika@vibhuayu.com', 2),
            ('eng008', 'Daniel', 'daniel@vibhuayu.com', 6),
            ('eng009', 'Karthik', 'karthik@vibhuayu.com', 3),
            ('eng010', 'Hema', 'hema@vibhuayu.com', 4),
            ('eng011', 'Naveen', 'naveen@vibhuayu.com', 5),
            ('eng012', 'Srinivas', 'srinivas@vibhuayu.com', 3),
            ('eng013', 'Meera', 'meera@vibhuayu.com', 2),
            ('eng014', 'Suraj', 'suraj@vibhuayu.com', 4),
            ('eng015', 'Akhil', 'akhil@vibhuayu.com', 3),
            ('eng016', 'Vikas', 'vikas@vibhuayu.com', 5),
            ('eng017', 'Sahith', 'sahith@vibhuayu.com', 2),
            ('eng018', 'Sravan', 'sravan@vibhuayu.com', 4)
        ]
        
        for uid, name, email, exp in engineer_data:
            c.execute("""
                INSERT INTO users (id, username, display_name, email, password, is_admin, experience, department, created_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (uid, uid, name, email, hash_pass('password123'), 0, exp, 'Physical Design', datetime.now().isoformat()))
    
    conn.commit()
    conn.close()

def _time_ago(date_str):
    """Calculate time ago from date string"""
    try:
        date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        now = datetime.now()
        diff = now - date_obj
        
        if diff.days > 0:
            return f"{diff.days}d ago"
        elif diff.seconds > 3600:
            return f"{diff.seconds // 3600}h ago"
        elif diff.seconds > 60:
            return f"{diff.seconds // 60}m ago"
        else:
            return "Just now"
    except:
        return "Unknown"

# Routes
@app.route('/')
def home():
    if 'user_id' in session:
        if session.get('is_admin'):
            return redirect('/admin')
        return redirect('/student')
    return redirect('/login')

@app.route('/health')
def health():
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE username = ?', (username,))
        user = c.fetchone()
        conn.close()
        
        if user and check_pass(user[4], password):
            session['user_id'] = user[0]
            session['username'] = user[1]
            session['display_name'] = user[2]
            session['is_admin'] = bool(user[5])
            session['theme'] = user[10] if user[10] else 'light'
            
            # Update last login
            conn = sqlite3.connect(DATABASE)
            c = conn.cursor()
            c.execute('UPDATE users SET last_login = ? WHERE id = ?', 
                     (datetime.now().isoformat(), user[0]))
            conn.commit()
            conn.close()
            
            # Log analytics
            DatabaseManager.log_analytics('login', user[0])
            
            if bool(user[5]):
                return redirect('/admin')
            return redirect('/student')
    
    # Enhanced login page
    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
    <title>Vibhuayu Technologies - Enhanced PD Assessment</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        :root {
            --primary-color: #667eea;
            --secondary-color: #764ba2;
            --success-color: #10b981;
            --warning-color: #f59e0b;
            --error-color: #ef4444;
            --bg-primary: #0f172a;
            --bg-secondary: #1e293b;
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --surface: rgba(255, 255, 255, 0.98);
            --border: #e2e8f0;
        }
        
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            background: linear-gradient(135deg, var(--bg-primary) 0%, var(--bg-secondary) 100%); 
            min-height: 100vh; 
            display: flex; 
            align-items: center; 
            justify-content: center; 
            position: relative;
            overflow-x: hidden;
        }
        
        body::before {
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0; bottom: 0;
            background: 
                radial-gradient(circle at 30% 40%, rgba(102, 126, 234, 0.3) 0%, transparent 50%),
                radial-gradient(circle at 80% 80%, rgba(118, 75, 162, 0.15) 0%, transparent 50%);
            z-index: 1;
        }
        
        .container {
            position: relative; z-index: 2;
            background: var(--surface);
            backdrop-filter: blur(20px);
            border-radius: 24px;
            padding: 50px 40px;
            width: min(450px, 90vw);
            box-shadow: 0 25px 50px rgba(0, 0, 0, 0.25);
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        .logo-section {
            text-align: center;
            margin-bottom: 35px;
        }
        
        .logo {
            width: 80px; height: 80px;
            margin: 0 auto 20px;
            background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
            border-radius: 20px;
            display: flex; align-items: center; justify-content: center;
            color: white; font-size: 36px; font-weight: 900;
            box-shadow: 0 10px 30px rgba(102, 126, 234, 0.3);
            position: relative; overflow: hidden;
        }
px;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 20px; margin-bottom: 30px;
        }
        
        .stat-card {
            background: var(--surface);
            padding: 25px; border-radius: 20px; text-align: center;
            box-shadow: 0 8px 25px rgba(0,0,0,0.1);
            transition: transform 0.3s ease;
        }
        
        .stat-card:hover { transform: translateY(-5px); }
        
        .stat-number {
            font-size: 36px; font-weight: 800;
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            margin-bottom: 8px; line-height: 1;
        }
        
        .stat-label {
            color: var(--text-secondary); font-weight: 600;
            font-size: 14px; text-transform: uppercase; letter-spacing: 1px;
        }
        
        .stat-subtitle {
            color: var(--text-secondary); font-size: 12px;
            margin-top: 5px;
        }
        
        .main-section {
            background: var(--surface);
            border-radius: 24px; padding: 35px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }
        
        .section-header {
            display: flex; justify-content: space-between; align-items: center;
            margin-bottom: 30px;
        }
        
        .section-title {
            color: var(--text-primary); font-size: 28px; font-weight: 700;
            display: flex; align-items: center; gap: 12px;
        }
        
        .assignment-card {
            background: linear-gradient(135deg, #f8fafc, #f1f5f9);
            border-radius: 16px; padding: 25px; margin: 20px 0;
            box-shadow: 0 4px 15px rgba(0,0,0,0.05);
            transition: all 0.3s ease; position: relative;
            overflow: hidden;
        }
        
        .assignment-card::before {
            content: ''; position: absolute; top: 0; left: 0;
            width: 4px; height: 100%;
        }
        
        .assignment-card.pending::before { background: var(--primary); }
        .assignment-card.submitted::before { background: var(--warning); }
        .assignment-card.completed::before { background: var(--success); }
        
        .assignment-card:hover {
            transform: translateY(-3px);
            box-shadow: 0 8px 25px rgba(0,0,0,0.1);
        }
        
        .assignment-header {
            display: flex; justify-content: space-between; align-items: center;
            margin-bottom: 15px;
        }
        
        .assignment-header h3 {
            color: var(--text-primary); font-size: 20px; margin: 0;
        }
        
        .score-display {
            background: var(--success); color: white;
            padding: 6px 15px; border-radius: 20px;
            font-weight: 700; font-size: 16px;
        }
        
        .due-date {
            background: var(--primary); color: white;
            padding: 6px 15px; border-radius: 20px;
            font-weight: 600; font-size: 14px;
        }
        
        .status-display {
            background: var(--warning); color: white;
            padding: 6px 15px; border-radius: 20px;
            font-weight: 600; font-size: 14px;
        }
        
        .assignment-meta {
            color: var(--text-secondary); font-size: 14px;
            margin-bottom: 15px; line-height: 1.5;
        }
        
        .start-btn {
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            color: white; padding: 12px 25px; text-decoration: none;
            border-radius: 10px; display: inline-block;
            font-weight: 600; transition: all 0.3s ease;
        }
        
        .start-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 20px rgba(102, 126, 234, 0.4);
        }
        
        .status-badge {
            padding: 8px 16px; border-radius: 20px;
            font-size: 12px; font-weight: 600;
            display: inline-block; margin-top: 10px;
        }
        
        .status-badge.pending {
            background: rgba(102, 126, 234, 0.1); color: var(--primary);
        }
        
        .status-badge.submitted {
            background: rgba(245, 158, 11, 0.1); color: var(--warning);
        }
        
        .status-badge.completed {
            background: rgba(16, 185, 129, 0.1); color: var(--success);
        }
        
        .no-assignments {
            text-align: center; padding: 80px 20px;
            color: var(--text-secondary);
        }
        
        .empty-icon {
            font-size: 64px; margin-bottom: 20px; opacity: 0.7;
        }
        
        .progress-section {
            background: linear-gradient(135deg, #f0f9ff, #e0f2fe);
            border-radius: 16px; padding: 25px; margin-top: 30px;
        }
        
        .progress-title {
            color: var(--text-primary); font-weight: 700;
            margin-bottom: 15px; text-align: center;
        }
        
        .progress-bar {
            background: #e2e8f0; height: 8px; border-radius: 4px;
            overflow: hidden; margin-bottom: 15px;
        }
        
        .progress-fill {
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            height: 100%; transition: width 0.3s ease;
        }
        
        .progress-text {
            text-align: center; color: var(--text-secondary);
            font-size: 14px; font-weight: 600;
        }
        
        @media (max-width: 768px) {
            .header-content {
                flex-direction: column; gap: 15px; text-align: center;
            }
            
            .stats-grid {
                grid-template-columns: repeat(2, 1fr);
            }
            
            .assignment-header {
                flex-direction: column; align-items: flex-start; gap: 10px;
            }
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="header-content">
            <div class="user-info">
                <div class="user-avatar">{{ user[2][:1].upper() }}</div>
                <div class="welcome-text">
                    <h1>Welcome back, {{ user[2] }}! 👋</h1>
                    <p>{{ user[6] }}+ years experience in Physical Design</p>
                </div>
            </div>
            <div class="nav-actions">
                <a href="/logout" class="nav-btn">🚪 Logout</a>
            </div>
        </div>
    </div>
    
    <div class="container">
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-number">{{ total_assignments }}</div>
                <div class="stat-label">Total Assigned</div>
                <div class="stat-subtitle">All assessments</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ pending }}</div>
                <div class="stat-label">Pending</div>
                <div class="stat-subtitle">Ready to start</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ completed }}</div>
                <div class="stat-label">Completed</div>
                <div class="stat-subtitle">Graded assessments</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ "%.1f"|format(avg_score) }}</div>
                <div class="stat-label">Average Score</div>
                <div class="stat-subtitle">Out of 10 points</div>
            </div>
        </div>
        
        <div class="main-section">
            <div class="section-header">
                <h2 class="section-title">📋 My Assessments</h2>
            </div>
            
            <div id="assignmentsContainer">
                {{ assignments_html|safe }}
            </div>
        </div>
        
        {% if completed > 0 %}
        <div class="progress-section">
            <div class="progress-title">📊 Your Progress</div>
            <div class="progress-bar">
                <div class="progress-fill" style="width: {{ (completed / total_assignments * 100)|round }}%;"></div>
            </div>
            <div class="progress-text">
                {{ completed }} of {{ total_assignments }} assessments completed ({{ (completed / total_assignments * 100)|round }}%)
            </div>
        </div>
        {% endif %}
    </div>
</body>
</html>""", 
    user=user,
    assignments_html=assignments_html,
    total_assignments=total_assignments,
    completed=completed,
    pending=pending,
    avg_score=avg_score
    )

@app.route('/student/test/<assignment_id>', methods=['GET', 'POST'])
def student_test(assignment_id):
    if not session.get('user_id') or session.get('is_admin'):
        return redirect('/login')
    
    user_id = session['user_id']
    
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    # Get assignment
    c.execute('SELECT * FROM assignments WHERE id = ? AND engineer_id = ?', (assignment_id, user_id))
    assignment = c.fetchone()
    
    if not assignment:
        conn.close()
        return redirect('/student')
    
    # Check if already submitted
    c.execute('SELECT * FROM submissions WHERE assignment_id = ? AND engineer_id = ?', (assignment_id, user_id))
    existing_submission = c.fetchone()
    
    if existing_submission:
        conn.close()
        return redirect('/student')
    
    questions = json.loads(assignment[3])
    
    # Handle submission
    if request.method == 'POST':
        answers = {}
        for i in range(len(questions)):
            answer = request.form.get(f'answer_{i}', '').strip()
            if answer:
                answers[str(i)] = answer
        
        if len(answers) >= 15:
            # Auto-score answers
            auto_scores = {}
            for i, answer in answers.items():
                if answer:
                    score_analysis = scoring_system.analyze_answer_comprehensive(
                        questions[int(i)], answer, assignment[2]
                    )
                    auto_scores[i] = score_analysis
            
            # Create submission
            submission_id = f"SUB_{assignment_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            c.execute('''
                INSERT INTO submissions 
                (id, assignment_id, engineer_id, answers, submitted_date, auto_scores, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (submission_id, assignment_id, user_id, json.dumps(answers),
                  datetime.now().isoformat(), json.dumps(auto_scores), 'submitted'))
            
            conn.commit()
            
            # Log analytics
            DatabaseManager.log_analytics('submission_created', user_id, {
                'assignment_id': assignment_id,
                'answers_count': len(answers),
                'topic': assignment[2]
            })
        
        conn.close()
        return redirect('/student')
    
    conn.close()
    
    # Build questions HTML
    questions_html = ''
    for i, question in enumerate(questions):
        questions_html += f'''
        <div class="question-card" data-question="{i}">
            <div class="question-header">
                <div class="question-number">Question {i+1} of {len(questions)}</div>
                <div class="topic-badge">{assignment[2].upper()}</div>
            </div>
            
            <div class="question-content">
                <div class="question-text">{question}</div>
                
                <div class="answer-section">
                    <label for="answer_{i}">Your Answer:</label>
                    <textarea id="answer_{i}" name="answer_{i}" 
                             placeholder="Provide a detailed technical answer..." 
                             required minlength="20"></textarea>
                    <div class="char-counter">
                        <span id="count_{i}">0</span> characters
                        <span class="min-requirement">(minimum 20 required)</span>
                    </div>
                </div>
            </div>
        </div>'''
    
    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
    <title>{{ assignment[2].upper() }} Assessment - Enhanced Experience</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        :root {
            --primary: #667eea;
            --secondary: #764ba2;
            --success: #10b981;
            --warning: #f59e0b;
            --error: #ef4444;
            --surface: rgba(255, 255, 255, 0.98);
        }
        
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%);
            min-height: 100vh;
        }
        
        .test-header {
            background: rgba(255,255,255,0.15);
            backdrop-filter: blur(20px);
            color: white; padding: 20px 0;
            position: sticky; top: 0; z-index: 100;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
        }
        
        .header-content {
            max-width: 1000px; margin: 0 auto; padding: 0 20px;
            display: flex; justify-content: space-between; align-items: center;
        }
        
        .test-info h1 {
            font-size: 24px; font-weight: 700; margin-bottom: 5px;
        }
        
        .test-meta {
            opacity: 0.9; font-size: 14px;
        }
        
        .progress-container {
            display: flex; align-items: center; gap: 15px;
        }
        
        .progress-circle {
            width: 60px; height: 60px;
            border-radius: 50%; background: rgba(255,255,255,0.2);
            display: flex; align-items: center; justify-content: center;
            font-weight: 700; font-size: 14px;
            border: 3px solid rgba(255,255,255,0.3);
        }
        
        .container {
            max-width: 1000px; margin: 20px auto; padding: 0 20px;
        }
        
        .test-overview {
            background: var(--surface); border-radius: 20px;
            padding: 30px; margin-bottom: 25px;
            box-shadow: 0 8px 25px rgba(0,0,0,0.1);
            text-align: center;
        }
        
        .overview-grid {
            display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 20px; margin-top: 20px;
        }
        
        .overview-item {
            text-align: center;
        }
        
        .overview-value {
            font-size: 24px; font-weight: 700; color: var(--primary);
            margin-bottom: 5px;
        }
        
        .overview-label {
            color: #64748b; font-size: 14px; font-weight: 600;
        }
        
        .progress-tracker {
            background: var(--surface); border-radius: 16px;
            padding: 20px; margin-bottom: 25px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }
        
        .progress-bar {
            background: #e2e8f0; height: 8px; border-radius: 4px;
            overflow: hidden; margin: 15px 0;
        }
        
        .progress-fill {
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            height: 100%; width: 0%; transition: width 0.3s ease;
        }
        
        .progress-text {
            display: flex; justify-content: space-between; align-items: center;
            font-weight: 600; color: #64748b;
        }
        
        .question-card {
            background: var(--surface); border-radius: 20px;
            padding: 30px; margin: 25px 0;
            box-shadow: 0 8px 25px rgba(0,0,0,0.1);
            transition: all 0.3s ease;
        }
        
        .question-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 12px 35px rgba(0,0,0,0.15);
        }
        
        .question-header {
            display: flex; justify-content: space-between; align-items: center;
            margin-bottom: 25px;
        }
        
        .question-number {
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            color: white; padding: 10px 20px; border-radius: 25px;
            font-weight: 700; font-size: 14px;
        }
        
        .topic-badge {
            background: #f1f5f9; color: #64748b;
            padding: 8px 16px; border-radius: 20px;
            font-size: 12px; font-weight: 600; text-transform: uppercase;
        }
        
        .question-content {
            line-height: 1.6;
        }
        
        .question-text {
            background: linear-gradient(135deg, #f8fafc, #f1f5f9);
            padding: 25px; border-radius: 16px; margin-bottom: 25px;
            border-left: 4px solid var(--primary);
            font-size: 16px; line-height: 1.7;
        }
        
        .answer-section label {
            display: block; margin-bottom: 10px;
            font-weight: 600; color: #374151; font-size: 16px;
        }
        
        textarea {
            width: 100%; min-height: 140px; padding: 20px;
            border: 2px solid #e5e7eb; border-radius: 16px;
            font-size: 15px; font-family: inherit; resize: vertical;
            transition: all 0.3s ease; line-height: 1.6;
        }
        
        textarea:focus {
            outline: none; border-color: var(--primary);
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }
        
        .char-counter {
            display: flex; justify-content: space-between; align-items: center;
            margin-top: 8px; font-size: 13px;
        }
        
        .min-requirement {
            color: #64748b;
        }
        
        .submit-section {
            background: var(--surface); border-radius: 20px;
            padding: 40px; margin-top: 40px; text-align: center;
            box-shadow: 0 8px 25px rgba(0,0,0,0.1);
        }
        
        .warning-box {
            background: #fef3c7; border: 2px solid #f59e0b;
            padding: 20px; border-radius: 16px; margin-bottom: 25px;
            display: flex; align-items: center; gap: 15px;
        }
        
        .warning-icon {
            font-size: 24px;
        }
        
        .btn {
            padding: 15px 30px; border: none; border-radius: 12px;
            font-weight: 600; cursor: pointer; margin: 8px;
            text-decoration: none; display: inline-block;
            transition: all 0.3s ease; font-size: 16px;
        }
        
        .btn-primary {
            background: linear-gradient(135deg, var(--success), #059669);
            color: white;
        }
        
        .btn-secondary {
            background: #6b7280; color: white;
        }
        
        .btn:hover { transform: translateY(-2px); }
        
        .btn:disabled {
            opacity: 0.6; cursor: not-allowed;
            transform: none !important;
        }
        
        @media (max-width: 768px) {
            .header-content {
                flex-direction: column; gap: 15px; text-align: center;
            }
            
            .overview-grid {
                grid-template-columns: repeat(2, 1fr);
            }
            
            .question-header {
                flex-direction: column; gap: 10px; align-items: flex-start;
            }
        }
    </style>
</head>
<body>
    <div class="test-header">
        <div class="header-content">
            <div class="test-info">
                <h1>📝 {{ assignment[2].upper() }} Assessment</h1>
                <div class="test-meta">Enhanced Physical Design Evaluation</div>
            </div>
            <div class="progress-container">
                <div class="progress-circle" id="progressCircle">0%</div>
            </div>
        </div>
    </div>
    
    <div class="container">
        <div class="test-overview">
            <h2>📋 Assessment Overview</h2>
            <div class="overview-grid">
                <div class="overview-item">
                    <div class="overview-value">{{ len(questions) }}</div>
                    <div class="overview-label">Questions</div>
                </div>
                <div class="overview-item">
                    <div class="overview-value">{{ len(questions) * 10 }}</div>
                    <div class="overview-label">Max Points</div>
                </div>
                <div class="overview-item">
                    <div class="overview-value">{{ assignment[5][:10] }}</div>
                    <div class="overview-label">Due Date</div>
                </div>
                <div class="overview-item">
                    <div class="overview-value">{{ assignment[2].upper() }}</div>
                    <div class="overview-label">Topic</div>
                </div>
            </div>
        </div>
        
        <div class="progress-tracker">
            <div class="progress-text">
                <span>Progress</span>
                <span id="progressText">0 of {{ len(questions) }} answered</span>
            </div>
            <div class="progress-bar">
                <div class="progress-fill" id="progressBar"></div>
            </div>
        </div>
        
        <form method="POST" id="assessmentForm">
            {{ questions_html|safe }}
            
            <div class="submit-section">
                <div class="warning-box">
                    <div class="warning-icon">⚠️</div>
                    <div>
                        <strong>Important Notice:</strong> Review all answers carefully before submitting. 
                        You cannot edit your responses after submission. Minimum 15 questions must be answered.
                    </div>
                </div>
                
                <button type="submit" class="btn btn-primary" id="submitBtn" disabled>
                    🚀 Submit Assessment
                </button>
                <a href="/student" class="btn btn-secondary">💾 Save & Exit Later</a>
            </div>
        </form>
    </div>
    
    <script>
        const totalQuestions = {{ len(questions) }};
        const textareas = document.querySelectorAll('textarea');
        const progressBar = document.getElementById('progressBar');
        const progressText = document.getElementById('progressText');
        const progressCircle = document.getElementById('progressCircle');
        const submitBtn = document.getElementById('submitBtn');
        
        // Initialize
        setupEventListeners();
        loadAutoSavedData();
        updateProgress();
        
        function setupEventListeners() {
            textareas.forEach((textarea, index) => {
                const counter = document.getElementById(`count_${index}`);
                
                textarea.addEventListener('input', function() {
                    const length = this.value.length;
                    counter.textContent = length;
                    
                    // Color coding for minimum requirement
                    if (length < 20) {
                        counter.style.color = '#ef4444';
                    } else if (length < 50) {
                        counter.style.color = '#f59e0b';
                    } else {
                        counter.style.color = '#10b981';
                    }
                    
                    updateProgress();
                    autoSave();
                });
                
                // Auto-resize textarea
                textarea.addEventListener('input', function() {
                    this.style.height = 'auto';
                    this.style.height = Math.max(140, this.scrollHeight) + 'px';
                });
            });
            
            // Form submission
            document.getElementById('assessmentForm').addEventListener('submit', function(e) {
                const answeredCount = getAnsweredCount();
                
                if (answeredCount < 15) {
                    e.preventDefault();
                    alert(`Please answer at least 15 questions. Currently answered: ${answeredCount}`);
                    return false;
                }
                
                const confirmed = confirm(
                    `Are you sure you want to submit your assessment?\\n\\n` +
                    `• Questions answered: ${answeredCount}/${totalQuestions}\\n` +
                    `• This action cannot be undone\\n` +
                    `• Your responses will be final\\n\\n` +
                    `Click OK to submit or Cancel to continue editing.`
                );
                
                if (!confirmed) {
                    e.preventDefault();
                    return false;
                }
                
                // Clear auto-saved data
                clearAutoSavedData();
            });
        }
        
        function updateProgress() {
            const answeredCount = getAnsweredCount();
            const percentage = (answeredCount / totalQuestions) * 100;
            
            progressBar.style.width = percentage + '%';
            progressText.textContent = `${answeredCount} of ${totalQuestions} answered`;
            progressCircle.textContent = Math.round(percentage) + '%';
            
            // Enable submit if at least 15 questions answered
            const meetsMinimum = answeredCount >= 15;
            submitBtn.disabled = !meetsMinimum;
            
            if (meetsMinimum) {
                submitBtn.style.opacity = '1';
                submitBtn.textContent = `🚀 Submit Assessment (${answeredCount}/${totalQuestions})`;
            } else {
                submitBtn.style.opacity = '0.6';
                submitBtn.textContent = `Answer ${15 - answeredCount} more to submit`;
            }
        }
        
        function getAnsweredCount() {
            return Array.from(textareas).filter(ta => ta.value.trim().length >= 20).length;
        }
        
        function autoSave() {
            const formData = {};
            textareas.forEach((textarea, index) => {
                formData[`answer_${index}`] = textarea.value;
            });
            
            localStorage.setItem(`assessment_{{ assignment[0] }}`, JSON.stringify({
                data: formData,
                timestamp: Date.now()
            }));
        }
        
        function loadAutoSavedData() {
            const saved = localStorage.getItem(`assessment_{{ assignment[0] }}`);
            if (saved) {
                try {
                    const { data } = JSON.parse(saved);
                    
                    textareas.forEach((textarea, index) => {
                        const savedValue = data[`answer_${index}`];
                        if (savedValue) {
                            textarea.value = savedValue;
                            textarea.dispatchEvent(new Event('input'));
                        }
                    });
                    
                    console.log('✅ Auto-saved data loaded');
                } catch (e) {
                    console.warn('Failed to load auto-saved data');
                }
            }
        }
        
        function clearAutoSavedData() {
            localStorage.removeItem(`assessment_{{ assignment[0] }}`);
        }
        
        // Auto-save every 30 seconds
        setInterval(() => {
            if (getAnsweredCount() > 0) {
                autoSave();
            }
        }, 30000);
        
        // Prevent accidental page leave
        window.addEventListener('beforeunload', function(e) {
            const answeredCount = getAnsweredCount();
            if (answeredCount > 0) {
                e.preventDefault();
                e.returnValue = 'You have unsaved answers. Are you sure you want to leave?';
                return e.returnValue;
            }
        });
        
        console.log('🚀 Enhanced assessment experience loaded');
        console.log(`📊 Assessment: {{ assignment[2].upper() }} with ${totalQuestions} questions`);
    </script>
</body>
</html>""", 
    assignment=assignment,
    questions=questions,
    questions_html=questions_html
    )

# Additional utility routes
@app.route('/admin/stats')
def admin_stats():
    if not session.get('is_admin'):
        return jsonify({'error': 'Unauthorized'}), 403
    
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    c.execute('SELECT COUNT(*) FROM users WHERE is_admin = 0')
    engineers = c.fetchone()[0]
    
    c.execute('SELECT COUNT(*) FROM assignments')
    assignments = c.fetchone()[0]
    
    c.execute('SELECT COUNT(*) FROM submissions WHERE status = "submitted"')
    pending = c." if suggested_score >= 5 else "#ef4444"
        
        questions_html += f'''
        <div class="question-review-card">
            <div class="question-header">
                <h3>Question {i+1}</h3>
                <div class="ai-score-badge" style="background: {color};">
                    AI Score: {suggested_score}/10
                </div>
            </div>
            
            <div class="question-text">
                <strong>Question:</strong><br>
                {question}
            </div>
            
            <div class="answer-section">
                <strong>Engineer's Answer:</strong>
                <div class="answer-text">{answer}</div>
            </div>
            
            <div class="scoring-analysis">
                <div class="score-breakdown">
                    <h4>AI Analysis Breakdown:</h4>
                    <div class="breakdown-grid">
                        <div class="breakdown-item">
                            <span>Technical:</span>
                            <span>{breakdown['technical']}/10</span>
                        </div>
                        <div class="breakdown-item">
                            <span>Depth:</span>
                            <span>{breakdown['depth']}/10</span>
                        </div>
                        <div class="breakdown-item">
                            <span>Methodology:</span>
                            <span>{breakdown['methodology']}/10</span>
                        </div>
                        <div class="breakdown-item">
                            <span>Clarity:</span>
                            <span>{breakdown['clarity']}/10</span>
                        </div>
                    </div>
                </div>
                
                <div class="ai-suggestions">
                    <h4>Improvement Suggestions:</h4>
                    <ul>
                        {''.join([f'<li>{suggestion}</li>' for suggestion in suggestions[:3]])}
                    </ul>
                </div>
            </div>
            
            <div class="manual-grading">
                <div class="grade-input">
                    <label>Your Score:</label>
                    <input type="number" name="score_{i}" min="0" max="10" step="0.1" 
                           value="{suggested_score}" class="score-input">
                    <button type="button" onclick="this.previousElementSibling.value='{suggested_score}'" 
                            class="use-ai-btn">Use AI Score</button>
                </div>
                <div class="feedback-input">
                    <label>Additional Feedback:</label>
                    <textarea name="feedback_{i}" placeholder="Optional: Add specific feedback for this answer..."></textarea>
                </div>
            </div>
        </div>'''
    
    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
    <title>Review Assessment - Enhanced Admin</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        :root {
            --primary: #667eea;
            --secondary: #764ba2;
            --success: #10b981;
            --warning: #f59e0b;
            --error: #ef4444;
            --surface: #ffffff;
            --bg-light: #f8fafc;
        }
        
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
            min-height: 100vh;
        }
        
        .header {
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            color: white; padding: 20px 0;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
        }
        
        .header-content {
            max-width: 1200px; margin: 0 auto; padding: 0 20px;
            display: flex; justify-content: space-between; align-items: center;
        }
        
        .container {
            max-width: 1200px; margin: 20px auto; padding: 0 20px;
        }
        
        .submission-info {
            background: var(--surface); border-radius: 16px;
            padding: 25px; margin-bottom: 25px;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
        }
        
        .info-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
        }
        
        .info-item {
            text-align: center;
        }
        
        .info-value {
            font-size: 24px; font-weight: 700;
            color: var(--primary); margin-bottom: 5px;
        }
        
        .info-label {
            color: #64748b; font-size: 14px; font-weight: 600;
        }
        
        .question-review-card {
            background: var(--surface); border-radius: 16px;
            padding: 25px; margin: 20px 0;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
            border-left: 4px solid var(--primary);
        }
        
        .question-header {
            display: flex; justify-content: space-between;
            align-items: center; margin-bottom: 20px;
        }
        
        .question-header h3 {
            color: #1e293b; font-size: 18px;
        }
        
        .ai-score-badge {
            color: white; padding: 6px 15px;
            border-radius: 20px; font-weight: 600; font-size: 14px;
        }
        
        .question-text {
            background: var(--bg-light); padding: 15px;
            border-radius: 8px; margin-bottom: 15px;
            border-left: 3px solid var(--primary);
        }
        
        .answer-section {
            margin-bottom: 20px;
        }
        
        .answer-text {
            background: #fefefe; border: 1px solid #e2e8f0;
            padding: 15px; border-radius: 8px; margin-top: 8px;
            line-height: 1.6; white-space: pre-wrap;
            max-height: 200px; overflow-y: auto;
        }
        
        .scoring-analysis {
            background: var(--bg-light); border-radius: 12px;
            padding: 20px; margin-bottom: 20px;
        }
        
        .breakdown-grid {
            display: grid; grid-template-columns: repeat(2, 1fr);
            gap: 10px; margin-top: 10px;
        }
        
        .breakdown-item {
            display: flex; justify-content: space-between;
            padding: 8px 12px; background: white; border-radius: 6px;
        }
        
        .ai-suggestions {
            margin-top: 15px;
        }
        
        .ai-suggestions ul {
            margin-top: 8px; padding-left: 20px;
        }
        
        .ai-suggestions li {
            margin-bottom: 5px; color: #64748b;
        }
        
        .manual-grading {
            display: grid; grid-template-columns: 1fr 2fr; gap: 20px;
            padding-top: 20px; border-top: 1px solid #e2e8f0;
        }
        
        .grade-input {
            display: flex; flex-direction: column; gap: 10px;
        }
        
        .score-input {
            padding: 8px 12px; border: 2px solid #e2e8f0;
            border-radius: 6px; font-size: 16px; width: 80px;
        }
        
        .use-ai-btn {
            padding: 6px 12px; background: var(--primary);
            color: white; border: none; border-radius: 6px;
            cursor: pointer; font-size: 12px;
        }
        
        .feedback-input textarea {
            width: 100%; height: 80px; padding: 10px;
            border: 2px solid #e2e8f0; border-radius: 6px;
            resize: vertical; font-family: inherit;
        }
        
        .submit-section {
            background: var(--surface); border-radius: 16px;
            padding: 25px; margin-top: 30px; text-align: center;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
        }
        
        .btn {
            padding: 12px 25px; border: none; border-radius: 8px;
            font-weight: 600; cursor: pointer; margin: 5px;
            text-decoration: none; display: inline-block;
            transition: all 0.3s ease;
        }
        
        .btn-primary {
            background: linear-gradient(135deg, var(--success), #059669);
            color: white;
        }
        
        .btn-secondary {
            background: #6b7280; color: white;
        }
        
        .btn:hover { transform: translateY(-2px); }
        
        .total-calculator {
            background: var(--primary); color: white;
            padding: 15px; border-radius: 12px; margin-bottom: 20px;
            text-align: center; font-weight: 600;
        }
        
        @media (max-width: 768px) {
            .manual-grading { grid-template-columns: 1fr; }
            .breakdown-grid { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="header-content">
            <h1>📝 Review Assessment</h1>
            <a href="/admin" class="btn btn-secondary">← Back to Dashboard</a>
        </div>
    </div>
    
    <div class="container">
        <div class="submission-info">
            <div class="info-grid">
                <div class="info-item">
                    <div class="info-value">{{ submission[13] }}</div>
                    <div class="info-label">Engineer</div>
                </div>
                <div class="info-item">
                    <div class="info-value">{{ submission[11].upper() }}</div>
                    <div class="info-label">Topic</div>
                </div>
                <div class="info-item">
                    <div class="info-value">{{ len(questions) }}</div>
                    <div class="info-label">Questions</div>
                </div>
                <div class="info-item">
                    <div class="info-value">{{ submission[4][:10] }}</div>
                    <div class="info-label">Submitted</div>
                </div>
            </div>
        </div>
        
        <form method="POST" id="gradingForm">
            <div class="total-calculator">
                <span>Total Score: </span>
                <span id="totalScore">0</span>
                <span>/{{ len(questions) * 10 }} points</span>
                <span style="margin-left: 20px;">Average: </span>
                <span id="averageScore">0.0</span>
                <span>/10</span>
            </div>
            
            {{ questions_html|safe }}
            
            <div class="submit-section">
                <div style="background: #fef3c7; padding: 15px; border-radius: 8px; margin-bottom: 20px; color: #92400e;">
                    ⚠️ <strong>Review carefully:</strong> Grades will be final once submitted.
                </div>
                <button type="submit" class="btn btn-primary">✅ Submit Final Grades</button>
                <a href="/admin" class="btn btn-secondary">Cancel Review</a>
            </div>
        </form>
    </div>
    
    <script>
        // Calculate total score dynamically
        function updateTotal() {
            const scoreInputs = document.querySelectorAll('.score-input');
            let total = 0;
            let count = 0;
            
            scoreInputs.forEach(input => {
                const value = parseFloat(input.value) || 0;
                total += value;
                count++;
            });
            
            document.getElementById('totalScore').textContent = total.toFixed(1);
            document.getElementById('averageScore').textContent = (total / count).toFixed(1);
        }
        
        // Add event listeners to all score inputs
        document.querySelectorAll('.score-input').forEach(input => {
            input.addEventListener('input', updateTotal);
        });
        
        // Initial calculation
        updateTotal();
        
        // Form validation
        document.getElementById('gradingForm').addEventListener('submit', function(e) {
            if (!confirm('Are you sure you want to submit these grades? This action cannot be undone.')) {
                e.preventDefault();
            }
        });
    </script>
</body>
</html>""", 
    submission=submission,
    questions=questions,
    answers=answers,
    auto_scores=auto_scores,
    questions_html=questions_html
    )

@app.route('/admin/analytics')
def admin_analytics():
    if not session.get('is_admin'):
        return redirect('/login')
    
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    # Comprehensive analytics queries
    analytics_data = {}
    
    # Topic performance
    c.execute('''
        SELECT 
            a.topic,
            COUNT(s.id) as submissions,
            AVG(CAST(s.total_score as FLOAT)) as avg_score,
            MAX(CAST(s.total_score as FLOAT)) as max_score,
            MIN(CAST(s.total_score as FLOAT)) as min_score
        FROM assignments a
        LEFT JOIN submissions s ON a.id = s.assignment_id AND s.status = 'graded'
        GROUP BY a.topic
    ''')
    analytics_data['topic_performance'] = c.fetchall()
    
    # Engineer performance
    c.execute('''
        SELECT 
            u.display_name,
            u.experience,
            COUNT(s.id) as completed,
            AVG(CAST(s.total_score as FLOAT)) as avg_score,
            MAX(CAST(s.total_score as FLOAT)) as best_score
        FROM users u
        LEFT JOIN submissions s ON u.id = s.engineer_id AND s.status = 'graded'
        WHERE u.is_admin = 0
        GROUP BY u.id
        ORDER BY avg_score DESC
    ''')
    analytics_data['engineer_performance'] = c.fetchall()
    
    conn.close()
    
    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
    <title>Performance Analytics - Enhanced Admin</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.9.1/chart.min.js"></script>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
            margin: 0; min-height: 100vh; color: white;
        }
        
        .analytics-container {
            max-width: 1400px; margin: 0 auto; padding: 20px;
        }
        
        .analytics-grid {
            display: grid; grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 25px; margin: 25px 0;
        }
        
        .chart-card {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 20px; padding: 25px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
        }
        
        .chart-title {
            color: #1e293b; font-size: 18px; font-weight: 700;
            margin-bottom: 20px; text-align: center;
        }
        
        .stats-overview {
            display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px; margin-bottom: 30px;
        }
        
        .stat-box {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 16px; padding: 20px; text-align: center;
            backdrop-filter: blur(10px);
        }
        
        .stat-number {
            font-size: 32px; font-weight: 800; margin-bottom: 5px;
        }
        
        .performance-table {
            width: 100%; border-collapse: collapse; margin-top: 15px;
        }
        
        .performance-table th,
        .performance-table td {
            padding: 12px; text-align: left; border-bottom: 1px solid #e2e8f0;
        }
        
        .performance-table th {
            background: #f8fafc; font-weight: 600; color: #1e293b;
        }
        
        .score-badge {
            padding: 4px 12px; border-radius: 20px; font-weight: 600;
            font-size: 12px; color: white;
        }
        
        .score-excellent { background: #10b981; }
        .score-good { background: #f59e0b; }
        .score-needs-improvement { background: #ef4444; }
    </style>
</head>
<body>
    <div class="analytics-container">
        <div style="text-align: center; margin-bottom: 30px;">
            <h1 style="font-size: 36px; margin-bottom: 10px;">📊 Performance Analytics</h1>
            <p style="color: #94a3b8;">Comprehensive insights into assessment performance</p>
            <a href="/admin" style="color: #667eea; text-decoration: none;">← Back to Dashboard</a>
        </div>
        
        <div class="stats-overview">
            <div class="stat-box">
                <div class="stat-number" style="color: #667eea;">{{ analytics_data.topic_performance|length }}</div>
                <div>Active Topics</div>
            </div>
            <div class="stat-box">
                <div class="stat-number" style="color: #10b981;">{{ analytics_data.engineer_performance|length }}</div>
                <div>Engineers</div>
            </div>
            <div class="stat-box">
                <div class="stat-number" style="color: #f59e0b;">
                    {% set total_submissions = analytics_data.topic_performance|map(attribute=1)|sum %}
                    {{ total_submissions }}
                </div>
                <div>Total Submissions</div>
            </div>
            <div class="stat-box">
                <div class="stat-number" style="color: #8b5cf6;">
                    {% if analytics_data.topic_performance %}
                        {% set avg_score = (analytics_data.topic_performance|map(attribute=2)|sum) / (analytics_data.topic_performance|length) %}
                        {{ "%.1f"|format(avg_score) }}
                    {% else %}
                        0.0
                    {% endif %}
                </div>
                <div>Average Score</div>
            </div>
        </div>
        
        <div class="analytics-grid">
            <div class="chart-card">
                <div class="chart-title">📈 Topic Performance Overview</div>
                <canvas id="topicChart" width="400" height="300"></canvas>
            </div>
            
            <div class="chart-card">
                <div class="chart-title">👥 Engineer Performance Distribution</div>
                <canvas id="engineerChart" width="400" height="300"></canvas>
            </div>
        </div>
        
        <div class="chart-card">
            <div class="chart-title">🏆 Top Performers</div>
            <table class="performance-table">
                <thead>
                    <tr>
                        <th>Engineer</th>
                        <th>Experience</th>
                        <th>Completed</th>
                        <th>Average Score</th>
                        <th>Best Score</th>
                        <th>Performance</th>
                    </tr>
                </thead>
                <tbody>
                    {% for engineer in analytics_data.engineer_performance[:10] %}
                    <tr>
                        <td><strong>{{ engineer[0] }}</strong></td>
                        <td>{{ engineer[1] }}y</td>
                        <td>{{ engineer[2] }}</td>
                        <td>{{ "%.1f"|format(engineer[3] or 0) }}</td>
                        <td>{{ "%.1f"|format(engineer[4] or 0) }}</td>
                        <td>
                            {% set avg = engineer[3] or 0 %}
                            {% if avg >= 8 %}
                                <span class="score-badge score-excellent">Excellent</span>
                            {% elif avg >= 6 %}
                                <span class="score-badge score-good">Good</span>
                            {% else %}
                                <span class="score-badge score-needs-improvement">Needs Improvement</span>
                            {% endif %}
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
    
    <script>
        // Topic Performance Chart
        const topicData = {{ analytics_data.topic_performance|tojson }};
        const topicLabels = topicData.map(item => item[0].toUpperCase());
        const topicScores = topicData.map(item => item[2] || 0);
        
        new Chart(document.getElementById('topicChart'), {
            type: 'bar',
            data: {
                labels: topicLabels,
                datasets: [{
                    label: 'Average Score',
                    data: topicScores,
                    backgroundColor: ['#667eea', '#10b981', '#f59e0b'],
                    borderColor: ['#4f46e5', '#059669', '#d97706'],
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 10,
                        title: { display: true, text: 'Average Score' }
                    }
                }
            }
        });
        
        // Engineer Performance Distribution
        const engineerData = {{ analytics_data.engineer_performance|tojson }};
        const performanceBuckets = [0, 0, 0]; // [0-5, 5-7.5, 7.5-10]
        
        engineerData.forEach(engineer => {
            const score = engineer[3] || 0;
            if (score < 5) performanceBuckets[0]++;
            else if (score < 7.5) performanceBuckets[1]++;
            else performanceBuckets[2]++;
        });
        
        new Chart(document.getElementById('engineerChart'), {
            type: 'doughnut',
            data: {
                labels: ['Needs Improvement (0-5)', 'Good (5-7.5)', 'Excellent (7.5-10)'],
                datasets: [{
                    data: performanceBuckets,
                    backgroundColor: ['#ef4444', '#f59e0b', '#10b981'],
                    borderWidth: 2,
                    borderColor: '#fff'
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { position: 'bottom' }
                }
            }
        });
    </script>
</body>
</html>""", analytics_data=analytics_data)

@app.route('/student')
def student():
    if not session.get('user_id') or session.get('is_admin'):
        return redirect('/login')
    
    user_id = session['user_id']
    
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    # Get user details
    c.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    user = c.fetchone()
    
    # Get user's assignments
    c.execute('''
        SELECT a.*, s.status as submission_status, s.total_score, s.submitted_date
        FROM assignments a
        LEFT JOIN submissions s ON a.id = s.assignment_id AND a.engineer_id = s.engineer_id
        WHERE a.engineer_id = ?
        ORDER BY a.created_date DESC
    ''', (user_id,))
    assignments = c.fetchall()
    
    conn.close()
    
    # Build assignments HTML
    assignments_html = ''
    for assignment in assignments:
        status = assignment[11] or 'pending'
        score = assignment[12] or 0
        
        if status == 'graded':
            assignments_html += f'''
            <div class="assignment-card completed">
                <div class="assignment-header">
                    <h3>✅ {assignment[2].upper()} Assessment</h3>
                    <div class="score-display">{score}/180</div>
                </div>
                <div class="assignment-meta">
                    📊 Completed on {assignment[13][:10] if assignment[13] else 'Unknown'} | 
                    🎯 Score: {score} points
                </div>
                <div class="status-badge completed">Assessment Completed</div>
            </div>'''
        elif status == 'submitted':
            assignments_html += f'''
            <div class="assignment-card submitted">
                <div class="assignment-header">
                    <h3>⏳ {assignment[2].upper()} Assessment</h3>
                    <div class="status-display">Under Review</div>
                </div>
                <div class="assignment-meta">
                    📝 Submitted on {assignment[13][:10] if assignment[13] else 'Unknown'} | 
                    ⏰ Awaiting grades
                </div>
                <div class="status-badge submitted">Under Review</div>
            </div>'''
        else:
            assignments_html += f'''
            <div class="assignment-card pending">
                <div class="assignment-header">
                    <h3>🎯 {assignment[2].upper()} Assessment</h3>
                    <div class="due-date">Due: {assignment[5][:10]}</div>
                </div>
                <div class="assignment-meta">
                    📋 18 Smart Questions | 🎖️ Max: 180 points | 
                    ⏰ Due: {assignment[5][:10]}
                </div>
                <a href="/student/test/{assignment[0]}" class="start-btn">Start Assessment</a>
            </div>'''
    
    if not assignments_html:
        assignments_html = '''
        <div class="no-assignments">
            <div class="empty-icon">📭</div>
            <h3>No Assessments Yet</h3>
            <p>Your administrator will assign assessments soon. Check back later!</p>
        </div>'''
    
    # Calculate stats
    total_assignments = len(assignments)
    completed = len([a for a in assignments if (a[11] == 'graded')])
    pending = len([a for a in assignments if not a[11] or a[11] == 'pending'])
    avg_score = sum([a[12] for a in assignments if a[12]]) / max(completed, 1) if completed > 0 else 0
    
    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
    <title>Enhanced Engineer Dashboard - {{ user[2] }}</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        :root {
            --primary: #667eea;
            --secondary: #764ba2;
            --success: #10b981;
            --warning: #f59e0b;
            --error: #ef4444;
            --surface: rgba(255, 255, 255, 0.95);
            --text-primary: #1e293b;
            --text-secondary: #64748b;
        }
        
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%);
            min-height: 100vh;
        }
        
        .header {
            background: rgba(255,255,255,0.15);
            backdrop-filter: blur(20px);
            color: white; padding: 25px 0;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
        }
        
        .header-content {
            max-width: 1200px; margin: 0 auto; padding: 0 20px;
            display: flex; justify-content: space-between; align-items: center;
        }
        
        .user-info {
            display: flex; align-items: center; gap: 15px;
        }
        
        .user-avatar {
            width: 50px; height: 50px;
            background: rgba(255,255,255,0.2);
            border-radius: 50%; display: flex; align-items: center; justify-content: center;
            font-weight: 900; font-size: 20px;
            backdrop-filter: blur(10px);
        }
        
        .welcome-text h1 {
            font-size: 24px; font-weight: 700; margin-bottom: 5px;
        }
        
        .welcome-text p {
            opacity: 0.9; font-size: 14px;
        }
        
        .nav-actions {
            display: flex; gap: 15px;
        }
        
        .nav-btn {
            background: rgba(255,255,255,0.2);
            color: white; padding: 10px 15px;
            text-decoration: none; border-radius: 8px;
            backdrop-filter: blur(10px); transition: all 0.3s ease;
            font-weight: 600; font-size: 14px;
        }
        
        .nav-btn:hover {
            background: rgba(255,255,255,0.3);
            transform: translateY(-2px);
        }
        
        .container {
            max-width: 1200px; margin: 30px auto; padding: 0 20        
        .logo::before {
            content: ''; position: absolute;
            top: 0; left: 0; right: 0; bottom: 0;
            background: linear-gradient(45deg, transparent 30%, rgba(255,255,255,0.1) 50%, transparent 70%);
            transform: translateX(-100%);
            animation: shine 3s infinite;
        }
        
        @keyframes shine {
            0% { transform: translateX(-100%); }
            50% { transform: translateX(100%); }
            100% { transform: translateX(100%); }
        }
        
        .title {
            font-size: 28px; font-weight: 700;
            background: linear-gradient(135deg, #1e293b, #475569);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            margin-bottom: 8px;
        }
        
        .subtitle {
            color: #64748b; font-size: 16px; font-weight: 500;
            margin-bottom: 35px;
        }
        
        .form-group {
            margin-bottom: 24px;
        }
        
        .form-group label {
            display: block; margin-bottom: 8px;
            color: #374151; font-weight: 600; font-size: 14px;
        }
        
        .form-input {
            width: 100%; padding: 16px 20px;
            border: 2px solid var(--border);
            border-radius: 12px; font-size: 16px;
            transition: all 0.3s ease;
            background: rgba(255, 255, 255, 0.8);
        }
        
        .form-input:focus {
            outline: none; border-color: var(--primary-color);
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
            background: white;
        }
        
        .login-btn {
            width: 100%; padding: 16px;
            background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
            color: white; border: none; border-radius: 12px;
            font-size: 16px; font-weight: 600; cursor: pointer;
            transition: all 0.3s ease; margin-bottom: 30px;
        }
        
        .login-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 25px rgba(102, 126, 234, 0.4);
        }
        
        .info-card {
            background: linear-gradient(135deg, #f8fafc, #f1f5f9);
            border: 1px solid var(--border);
            border-radius: 16px; padding: 24px; text-align: center;
        }
        
        .credentials {
            background: white; border-radius: 8px; padding: 12px;
            margin: 12px 0; border-left: 4px solid var(--primary-color);
        }
        
        .feature-highlights {
            margin-top: 15px; font-size: 12px; color: #64748b;
            line-height: 1.6;
        }
        
        .new-badge {
            background: var(--success-color); color: white;
            padding: 2px 6px; border-radius: 10px;
            font-size: 10px; font-weight: 600; margin-left: 5px;
        }
        
        @media (max-width: 480px) {
            .container { padding: 30px 20px; }
            .title { font-size: 24px; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="logo-section">
            <div class="logo">V7</div>
            <div class="title">Enhanced PD Portal</div>
            <div class="subtitle">Advanced Assessment & Analytics System</div>
        </div>
        
        <form method="POST">
            <div class="form-group">
                <label>Username</label>
                <input type="text" name="username" class="form-input" 
                       placeholder="Enter your username" required autocomplete="username">
            </div>
            <div class="form-group">
                <label>Password</label>
                <input type="password" name="password" class="form-input" 
                       placeholder="Enter your password" required autocomplete="current-password">
            </div>
            <button type="submit" class="login-btn">Access Enhanced Portal</button>
        </form>
        
        <div class="info-card">
            <div style="font-weight: 700; margin-bottom: 16px;">🔐 Demo Credentials</div>
            <div class="credentials">
                <strong>Engineers:</strong> eng001 through eng018<br>
                <strong>Password:</strong> password123<br>
                <strong>Admin:</strong> admin / Vibhuaya@3006
            </div>
            <div class="feature-highlights">
                <strong>🚀 New Features:</strong><br>
                Smart Question Generation <span class="new-badge">NEW</span><br>
                Enhanced AI Scoring <span class="new-badge">NEW</span><br>
                Performance Analytics <span class="new-badge">NEW</span><br>
                Mobile-Responsive Design <span class="new-badge">NEW</span>
            </div>
        </div>
    </div>
</body>
</html>""")

@app.route('/logout')
def logout():
    user_id = session.get('user_id')
    if user_id:
        DatabaseManager.log_analytics('logout', user_id)
    
    session.clear()
    return redirect('/login')

@app.route('/admin')
def admin():
    if not session.get('is_admin'):
        return redirect('/login')
    
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    # Get comprehensive statistics
    c.execute('SELECT COUNT(*) FROM users WHERE is_admin = 0')
    total_engineers = c.fetchone()[0]
    
    c.execute('SELECT COUNT(*) FROM assignments')
    total_assignments = c.fetchone()[0]
    
    c.execute('SELECT COUNT(*) FROM submissions WHERE status = "submitted"')
    pending_reviews = c.fetchone()[0]
    
    c.execute('SELECT COUNT(*) FROM submissions WHERE status = "graded"')
    completed_reviews = c.fetchone()[0]
    
    # Get engineers for dropdown
    c.execute('SELECT * FROM users WHERE is_admin = 0 ORDER BY display_name')
    engineers = c.fetchall()
    
    # Get recent activity
    c.execute('''
        SELECT s.*, a.topic, u.display_name, a.created_date as assignment_date
        FROM submissions s
        JOIN assignments a ON s.assignment_id = a.id
        JOIN users u ON s.engineer_id = u.id
        WHERE s.status = "submitted"
        ORDER BY s.submitted_date DESC
        LIMIT 10
    ''')
    pending_submissions = c.fetchall()
    
    # Get performance analytics
    c.execute('''
        SELECT 
            topic,
            COUNT(*) as count,
            AVG(CAST(total_score as FLOAT)) as avg_score,
            MAX(CAST(total_score as FLOAT)) as max_score,
            MIN(CAST(total_score as FLOAT)) as min_score
        FROM submissions s
        JOIN assignments a ON s.assignment_id = a.id
        WHERE s.status = "graded" AND s.total_score > 0
        GROUP BY topic
    ''')
    topic_stats = c.fetchall()
    
    conn.close()
    
    # Build engineer options
    eng_options = ''
    for eng in engineers:
        exp_years = eng[6] if eng[6] else 3
        eng_options += f'<option value="{eng[0]}" data-exp="{exp_years}">{eng[2]} ({exp_years}y exp)</option>'
    
    # Build pending submissions HTML
    pending_html = ''
    for sub in pending_submissions:
        time_ago = _time_ago(sub[4])
        pending_html += f'''
        <div class="submission-card">
            <div class="submission-header">
                <h4>{sub[11]} - {sub[10].upper()}</h4>
                <span class="time-badge">{time_ago}</span>
            </div>
            <div class="submission-meta">
                📝 {len(json.loads(sub[3]))} answers | 🎯 Auto-scored | ⏰ {sub[4][:16]}
            </div>
            <div class="submission-actions">
                <a href="/admin/review/{sub[1]}" class="review-btn">Review & Grade</a>
            </div>
        </div>'''
    
    if not pending_html:
        pending_html = '''
        <div class="no-submissions">
            <div class="empty-icon">📭</div>
            <h3>All Caught Up!</h3>
            <p>No pending submissions to review. Great work!</p>
        </div>'''
    
    # Build analytics charts data
    analytics_data = {
        "topic_stats": [{"topic": stat[0], "count": stat[1], "avg_score": round(stat[2], 1)} for stat in topic_stats],
        "total_engineers": total_engineers,
        "completion_rate": round((completed_reviews / max(total_assignments, 1)) * 100, 1)
    }
    
    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
    <title>Enhanced Admin Dashboard - Vibhuayu</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        :root {
            --primary: #667eea;
            --secondary: #764ba2;
            --success: #10b981;
            --warning: #f59e0b;
            --error: #ef4444;
            --bg-dark: #0f172a;
            --bg-light: #1e293b;
            --surface: #ffffff;
            --text-primary: #1e293b;
            --text-secondary: #64748b;
            --border: #e2e8f0;
        }
        
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, var(--bg-dark) 0%, var(--bg-light) 100%);
            min-height: 100vh; color: var(--text-primary);
        }
        
        .header {
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            padding: 20px 0; box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
            position: relative; overflow: hidden;
        }
        
        .header::before {
            content: ''; position: absolute;
            top: 0; left: 0; right: 0; bottom: 0;
            background: linear-gradient(45deg, transparent 30%, rgba(255,255,255,0.1) 50%, transparent 70%);
            transform: translateX(-100%);
            animation: headerShine 4s infinite;
        }
        
        @keyframes headerShine {
            0% { transform: translateX(-100%); }
            50% { transform: translateX(100%); }
            100% { transform: translateX(100%); }
        }
        
        .header-content {
            max-width: 1400px; margin: 0 auto; padding: 0 20px;
            display: flex; align-items: center; justify-content: space-between;
            position: relative; z-index: 2;
        }
        
        .header-title {
            display: flex; align-items: center; gap: 15px;
        }
        
        .header-logo {
            width: 50px; height: 50px;
            background: rgba(255, 255, 255, 0.15);
            border-radius: 12px; display: flex; align-items: center; justify-content: center;
            font-weight: 900; color: white; font-size: 20px;
            backdrop-filter: blur(10px);
        }
        
        .header h1 {
            color: white; font-size: 28px; font-weight: 700;
            text-shadow: 0 2px 10px rgba(0,0,0,0.3);
        }
        
        .nav-menu {
            display: flex; gap: 15px; align-items: center;
        }
        
        .nav-btn {
            background: rgba(255, 255, 255, 0.15); color: white;
            padding: 10px 15px; text-decoration: none; border-radius: 8px;
            backdrop-filter: blur(10px); transition: all 0.3s ease;
            font-weight: 600; font-size: 14px;
        }
        
        .nav-btn:hover {
            background: rgba(255, 255, 255, 0.25);
            transform: translateY(-2px);
        }
        
        .container {
            max-width: 1400px; margin: 30px auto; padding: 0 20px;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 25px; margin-bottom: 40px;
        }
        
        .stat-card {
            background: linear-gradient(135deg, var(--surface) 0%, #f8fafc 100%);
            padding: 30px; border-radius: 20px; text-align: center;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.2);
            transition: transform 0.3s ease;
        }
        
        .stat-card:hover { transform: translateY(-5px); }
        
        .stat-number {
            font-size: 42px; font-weight: 800;
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            margin-bottom: 8px; line-height: 1;
        }
        
        .stat-label {
            color: var(--text-secondary); font-weight: 600;
            font-size: 14px; text-transform: uppercase; letter-spacing: 1px;
        }
        
        .stat-trend {
            margin-top: 10px; font-size: 12px; font-weight: 600;
        }
        
        .trend-up { color: var(--success); }
        .trend-down { color: var(--error); }
        
        .main-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
        }
        
        .card {
            background: linear-gradient(135deg, var(--surface) 0%, #f8fafc 100%);
            border-radius: 20px; padding: 30px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.2);
        }
        
        .card h2 {
            color: var(--text-primary); margin-bottom: 25px;
            font-size: 24px; font-weight: 700;
            display: flex; align-items: center; gap: 10px;
        }
        
        .form-row {
            display: grid;
            grid-template-columns: 1fr 1fr auto;
            gap: 15px; align-items: end;
        }
        
        .form-group {
            display: flex; flex-direction: column;
        }
        
        .form-group label {
            margin-bottom: 8px; font-weight: 600;
            color: var(--text-primary); font-size: 14px;
        }
        
        select, button {
            padding: 14px 18px; border: 2px solid var(--border);
            border-radius: 12px; font-size: 16px;
            transition: all 0.3s ease; background: white;
            font-family: inherit;
        }
        
        select:focus {
            outline: none; border-color: var(--primary);
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }
        
        .btn-primary {
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            color: white; border: none; cursor: pointer;
            font-weight: 600; min-width: 140px;
        }
        
        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 25px rgba(102, 126, 234, 0.4);
        }
        
        .submission-card {
            background: linear-gradient(135deg, #f8fafc, #f1f5f9);
            padding: 20px; margin: 15px 0; border-radius: 16px;
            border-left: 4px solid var(--warning);
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.05);
            transition: all 0.3s ease;
        }
        
        .submission-card:hover {
            transform: translateX(5px);
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);
        }
        
        .submission-header {
            display: flex; justify-content: space-between;
            align-items: center; margin-bottom: 10px;
        }
        
        .submission-header h4 {
            color: var(--text-primary); margin: 0; font-size: 16px;
        }
        
        .time-badge {
            background: var(--warning); color: white;
            padding: 4px 12px; border-radius: 20px;
            font-size: 12px; font-weight: 600;
        }
        
        .submission-meta {
            color: var(--text-secondary); font-size: 14px;
            margin-bottom: 15px;
        }
        
        .submission-actions {
            display: flex; gap: 10px;
        }
        
        .review-btn {
            padding: 8px 16px; text-decoration: none;
            border-radius: 8px; font-weight: 600;
            font-size: 14px; transition: all 0.3s ease;
            background: linear-gradient(135deg, var(--success), #059669);
            color: white;
        }
        
        .review-btn:hover {
            transform: translateY(-2px);
        }
        
        .no-submissions {
            text-align: center; padding: 60px 20px;
            color: var(--text-secondary);
        }
        
        .empty-icon {
            font-size: 48px; margin-bottom: 20px;
        }
        
        .analytics-preview {
            background: linear-gradient(135deg, #f0f9ff, #e0f2fe);
            border-radius: 12px; padding: 20px;
            margin-top: 20px;
        }
        
        .analytics-item {
            display: flex; justify-content: space-between;
            align-items: center; padding: 10px 0;
            border-bottom: 1px solid rgba(102, 126, 234, 0.1);
        }
        
        .analytics-item:last-child { border-bottom: none; }
        
        @media (max-width: 768px) {
            .main-grid { grid-template-columns: 1fr; }
            .form-row { grid-template-columns: 1fr; gap: 15px; }
            .stats-grid { grid-template-columns: repeat(2, 1fr); }
            .header-content { flex-direction: column; gap: 15px; text-align: center; }
            .nav-menu { flex-wrap: wrap; justify-content: center; }
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="header-content">
            <div class="header-title">
                <div class="header-logo">V7</div>
                <h1>🚀 Enhanced Admin Dashboard</h1>
            </div>
            <div class="nav-menu">
                <a href="/admin/analytics" class="nav-btn">📊 Analytics</a>
                <a href="/logout" class="nav-btn">🚪 Logout</a>
            </div>
        </div>
    </div>
    
    <div class="container">
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-number">{{ total_engineers }}</div>
                <div class="stat-label">Engineers</div>
                <div class="stat-trend trend-up">↗ Active Users</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ total_assignments }}</div>
                <div class="stat-label">Assessments</div>
                <div class="stat-trend trend-up">📈 Total Created</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ pending_reviews }}</div>
                <div class="stat-label">Pending Reviews</div>
                <div class="stat-trend trend-up">⏳ Need Attention</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ analytics_data.completion_rate }}%</div>
                <div class="stat-label">Completion Rate</div>
                <div class="stat-trend trend-up">✅ Success Rate</div>
            </div>
        </div>
        
        <div class="main-grid">
            <div class="card">
                <h2>🎯 Create Smart Assessment</h2>
                <form method="POST" action="/admin/create">
                    <div class="form-row">
                        <div class="form-group">
                            <label>Select Engineer</label>
                            <select name="engineer_id" required id="engineerSelect">
                                <option value="">Choose engineer...</option>
                                {{ eng_options }}
                            </select>
                        </div>
                        <div class="form-group">
                            <label>Assessment Topic</label>
                            <select name="topic" required>
                                <option value="">Select topic...</option>
                                <option value="sta">🕒 STA (Static Timing Analysis)</option>
                                <option value="cts">🌳 CTS (Clock Tree Synthesis)</option>
                                <option value="signoff">✅ Signoff Checks & Verification</option>
                            </select>
                        </div>
                        <button type="submit" class="btn-primary">Create Assessment</button>
                    </div>
                    <div class="analytics-preview">
                        <div class="analytics-item">
                            <span>📝 Questions Generated:</span>
                            <strong>18 (Adaptive Difficulty)</strong>
                        </div>
                        <div class="analytics-item">
                            <span>🤖 AI Scoring:</span>
                            <strong>Enabled</strong>
                        </div>
                        <div class="analytics-item">
                            <span>📊 Analytics Tracking:</span>
                            <strong>Full Coverage</strong>
                        </div>
                    </div>
                </form>
            </div>
            
            <div class="card">
                <h2>📋 Pending Reviews ({{ pending_reviews }})</h2>
                <div style="max-height: 400px; overflow-y: auto;">
                    {{ pending_html|safe }}
                </div>
            </div>
        </div>
        
        {% if analytics_data.topic_stats %}
        <div class="card" style="margin-top: 30px;">
            <h2>📈 Performance Analytics</h2>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px;">
                {% for stat in analytics_data.topic_stats %}
                <div class="analytics-item">
                    <div>
                        <span style="background: var(--primary); color: white; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; text-transform: uppercase;">{{ stat.topic }}</span>
                        <div style="margin-top: 8px;">
                            <strong>{{ stat.count }}</strong> submissions<br>
                            <strong>{{ stat.avg_score }}</strong> avg score
                        </div>
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>
        {% endif %}
    </div>
    
    <script>
        // Enhanced interactivity
        document.getElementById('engineerSelect').addEventListener('change', function() {
            const selectedOption = this.selectedOptions[0];
            const experience = selectedOption.getAttribute('data-exp');
            if (experience) {
                console.log(`Selected engineer with ${experience} years experience`);
            }
        });
        
        // Auto-refresh pending count every 30 seconds
        setInterval(() => {
            fetch('/admin/stats')
                .then(response => response.json())
                .then(data => {
                    console.log('Stats updated');
                })
                .catch(err => console.log('Stats update failed'));
        }, 30000);
    </script>
</body>
</html>""", 
    total_engineers=total_engineers,
    total_assignments=total_assignments,
    pending_reviews=pending_reviews,
    completed_reviews=completed_reviews,
    eng_options=eng_options,
    pending_html=pending_html,
    analytics_data=analytics_data
    )

@app.route('/admin/create', methods=['POST'])
def admin_create():
    if not session.get('is_admin'):
        return redirect('/login')
    
    engineer_id = request.form.get('engineer_id')
    topic = request.form.get('topic')
    
    if not engineer_id or not topic:
        return redirect('/admin')
    
    # Get engineer experience for adaptive questions
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('SELECT experience FROM users WHERE id = ?', (engineer_id,))
    engineer = c.fetchone()
    experience = engineer[0] if engineer else 3
    
    # Generate smart questions
    questions = question_generator.generate_smart_questions(topic, 18, experience)
    
    # Create assignment
    assignment_id = f"PD_{topic}_{engineer_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    due_date = (datetime.now() + timedelta(days=7)).isoformat()
    
    c.execute("""
        INSERT INTO assignments (id, engineer_id, topic, questions, created_date, due_date, created_by)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (assignment_id, engineer_id, topic, json.dumps(questions), 
          datetime.now().isoformat(), due_date, session['user_id']))
    
    conn.commit()
    conn.close()
    
    # Log analytics
    DatabaseManager.log_analytics('assignment_created', session['user_id'], {
        'assignment_id': assignment_id,
        'topic': topic,
        'engineer_id': engineer_id
    })
    
    return redirect('/admin')

@app.route('/admin/review/<assignment_id>', methods=['GET', 'POST'])
def admin_review(assignment_id):
    if not session.get('is_admin'):
        return redirect('/login')
    
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    # Get submission details
    c.execute('''
        SELECT s.*, a.topic, a.questions, u.display_name
        FROM submissions s
        JOIN assignments a ON s.assignment_id = a.id
        JOIN users u ON s.engineer_id = u.id
        WHERE s.assignment_id = ?
    ''', (assignment_id,))
    submission = c.fetchone()
    
    if not submission:
        conn.close()
        return redirect('/admin')
    
    # Process submission data
    answers = json.loads(submission[3])
    questions = json.loads(submission[12])
    auto_scores = json.loads(submission[6]) if submission[6] else {}
    
    # Handle grading submission
    if request.method == 'POST':
        manual_scores = {}
        feedback_notes = {}
        total_score = 0
        
        for i in range(len(questions)):
            manual_score = request.form.get(f'score_{i}', 0)
            feedback_note = request.form.get(f'feedback_{i}', '')
            try:
                score = float(manual_score)
                manual_scores[str(i)] = score
                feedback_notes[str(i)] = feedback_note
                total_score += score
            except:
                manual_scores[str(i)] = 0
        
        # Update submission with grades
        c.execute('''
            UPDATE submissions 
            SET manual_scores = ?, feedback = ?, total_score = ?, 
                status = 'graded', graded_by = ?, graded_date = ?
            WHERE assignment_id = ?
        ''', (json.dumps(manual_scores), json.dumps(feedback_notes), 
              total_score, session['user_id'], datetime.now().isoformat(), assignment_id))
        conn.commit()
        conn.close()
        
        # Log analytics
        DatabaseManager.log_analytics('submission_graded', session['user_id'], {
            'assignment_id': assignment_id,
            'total_score': total_score,
            'engineer_id': submission[2]
        })
        
        return redirect('/admin')
    
    conn.close()
    
    # Build review interface
    questions_html = ''
    for i, question in enumerate(questions):
        answer = answers.get(str(i), 'No answer provided')
        auto_score_data = auto_scores.get(str(i), {})
        suggested_score = auto_score_data.get('score', 0)
        
        # Enhanced scoring analysis
        if answer and answer != 'No answer provided':
            score_analysis = scoring_system.analyze_answer_comprehensive(question, answer, submission[11])
            suggested_score = score_analysis['score']
            breakdown = score_analysis['breakdown']
            suggestions = score_analysis['suggestions']
        else:
            breakdown = {"technical": 0, "depth": 0, "methodology": 0, "clarity": 0}
            suggestions = ["Answer not provided"]
        
        color = "#10b981" if suggested_score >= 7 else "#f59e0b# Enhanced PD Assessment System - Complete app.py for Railway
import os
import hashlib
import json
import random
import sqlite3
from datetime import datetime, timedelta
from threading import Lock
from flask import Flask, request, redirect, session, jsonify, render_template_string
import re

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'pd-secret-key-enhanced')

# Database setup
DATABASE = 'enhanced_assessments.db'
db_lock = Lock()

class DatabaseManager:
    @staticmethod
    def init_db():
        """Initialize SQLite database with enhanced schema"""
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        
        # Users table
        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE,
                display_name TEXT,
                email TEXT,
                password TEXT,
                is_admin BOOLEAN DEFAULT 0,
                experience INTEGER DEFAULT 3,
                department TEXT,
                created_date TEXT,
                last_login TEXT,
                theme TEXT DEFAULT 'light'
            )
        """)
        
        # Assignments table
        c.execute("""
            CREATE TABLE IF NOT EXISTS assignments (
                id TEXT PRIMARY KEY,
                engineer_id TEXT,
                topic TEXT,
                questions TEXT,
                created_date TEXT,
                due_date TEXT,
                status TEXT DEFAULT 'pending',
                difficulty_level INTEGER DEFAULT 1,
                max_points INTEGER DEFAULT 180,
                created_by TEXT,
                FOREIGN KEY (engineer_id) REFERENCES users (id)
            )
        """)
        
        # Submissions table (enhanced)
        c.execute("""
            CREATE TABLE IF NOT EXISTS submissions (
                id TEXT PRIMARY KEY,
                assignment_id TEXT,
                engineer_id TEXT,
                answers TEXT,
                submitted_date TEXT,
                status TEXT DEFAULT 'submitted',
                auto_scores TEXT,
                manual_scores TEXT,
                feedback TEXT,
                total_score INTEGER DEFAULT 0,
                graded_by TEXT,
                graded_date TEXT,
                time_spent INTEGER DEFAULT 0,
                FOREIGN KEY (assignment_id) REFERENCES assignments (id),
                FOREIGN KEY (engineer_id) REFERENCES users (id)
            )
        """)
        
        # Analytics table
        c.execute("""
            CREATE TABLE IF NOT EXISTS analytics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT,
                user_id TEXT,
                data TEXT,
                timestamp TEXT
            )
        """)
        
        conn.commit()
        conn.close()
    
    @staticmethod
    def log_analytics(event_type, user_id, data=None):
        """Log analytics events"""
        with db_lock:
            conn = sqlite3.connect(DATABASE)
            c = conn.cursor()
            c.execute("""
                INSERT INTO analytics (event_type, user_id, data, timestamp)
                VALUES (?, ?, ?, ?)
            """, (event_type, user_id, json.dumps(data) if data else None, datetime.now().isoformat()))
            conn.commit()
            conn.close()

# Enhanced Question Generation with Smart AI
class SmartQuestionGenerator:
    def __init__(self):
        self.question_templates = {
            "sta": [
                {
                    "template": "Your design has {violation_type} violations of {violation_amount}ps on {num_paths} critical paths. The design is running at {frequency}MHz. Analyze the root causes and propose {num_solutions} specific solutions with expected improvement estimates.",
                    "difficulty": 3,
                    "parameters": {
                        "violation_type": ["setup", "hold", "max_transition"],
                        "violation_amount": [20, 50, 100, 150, 200],
                        "num_paths": [10, 25, 50, 100, 200],
                        "frequency": [500, 800, 1000, 1500, 2000],
                        "num_solutions": [3, 4, 5]
                    }
                },
                {
                    "template": "Explain the concept of {concept} in static timing analysis. How does it impact {impact_area} and what are the industry-standard approaches to handle it in {technology_node} designs?",
                    "difficulty": 2,
                    "parameters": {
                        "concept": ["clock jitter", "OCV", "useful skew", "clock latency", "timing corners"],
                        "impact_area": ["setup timing", "hold timing", "power consumption", "area optimization"],
                        "technology_node": ["7nm", "5nm", "3nm", "advanced nodes"]
                    }
                },
                {
                    "template": "You're analyzing a {design_type} with {num_domains} clock domains running at different frequencies. Describe your approach to handle clock domain crossings and ensure timing closure across all interfaces.",
                    "difficulty": 4,
                    "parameters": {
                        "design_type": ["SoC", "CPU", "GPU", "AI accelerator"],
                        "num_domains": [3, 4, 5, 6]
                    }
                }
            ],
            "cts": [
                {
                    "template": "Design a clock tree for a {design_size} design with {num_flops} flip-flops distributed across {die_size}. The target skew is {target_skew}ps and you have {buffer_types} buffer types available. Explain your tree topology choice and optimization strategy.",
                    "difficulty": 3,
                    "parameters": {
                        "design_size": ["large-scale", "medium-scale", "complex"],
                        "num_flops": [10000, 25000, 50000, 100000],
                        "die_size": ["5mm x 5mm", "10mm x 10mm", "15mm x 15mm"],
                        "target_skew": [25, 50, 75, 100],
                        "buffer_types": [3, 4, 5, 6]
                    }
                },
                {
                    "template": "Your clock tree has {power_consumption}mW power consumption, which is {percentage}% of total chip power. Propose {num_techniques} specific techniques to reduce clock power while maintaining {skew_constraint}ps skew constraint.",
                    "difficulty": 4,
                    "parameters": {
                        "power_consumption": [50, 100, 150, 200],
                        "percentage": [15, 20, 25, 30, 35],
                        "num_techniques": [3, 4, 5],
                        "skew_constraint": [30, 50, 75]
                    }
                }
            ],
            "signoff": [
                {
                    "template": "Your design failed {check_type} with {num_violations} violations. The violations are distributed as: {violation_dist}. Create a systematic debugging and resolution plan with priority ordering and estimated effort.",
                    "difficulty": 3,
                    "parameters": {
                        "check_type": ["DRC", "LVS", "Antenna", "Metal Density"],
                        "num_violations": [50, 100, 200, 500],
                        "violation_dist": ["70% spacing, 20% width, 10% via", "50% density, 30% spacing, 20% antenna"]
                    }
                },
                {
                    "template": "Perform signoff analysis for a {design_type} in {technology} process. The design has {power_domains} power domains and {io_count} I/Os. List all required signoff checks and create a verification plan with timeline.",
                    "difficulty": 4,
                    "parameters": {
                        "design_type": ["automotive SoC", "mobile processor", "IoT chip", "high-performance CPU"],
                        "technology": ["7nm FinFET", "5nm", "3nm GAA"],
                        "power_domains": [2, 3, 4, 5],
                        "io_count": [100, 200, 500, 1000]
                    }
                }
            ]
        }
    
    def generate_smart_questions(self, topic, num_questions=18, engineer_exp=3):
        """Generate questions with adaptive difficulty"""
        templates = self.question_templates.get(topic, [])
        if not templates:
            return self._fallback_questions(topic)
        
        questions = []
        difficulty_distribution = self._get_difficulty_distribution(engineer_exp, num_questions)
        
        for target_difficulty in difficulty_distribution:
            suitable_templates = [t for t in templates if abs(t["difficulty"] - target_difficulty) <= 1]
            if not suitable_templates:
                suitable_templates = templates
            
            template = random.choice(suitable_templates)
            question = self._generate_from_template(template)
            questions.append(question)
        
        return questions[:num_questions]
    
    def _get_difficulty_distribution(self, engineer_exp, num_questions):
        """Create difficulty distribution based on experience"""
        if engineer_exp <= 2:
            easy_count = int(num_questions * 0.6)
            medium_count = int(num_questions * 0.3)
            hard_count = num_questions - easy_count - medium_count
            return [2] * easy_count + [3] * medium_count + [4] * hard_count
        elif engineer_exp <= 4:
            easy_count = int(num_questions * 0.3)
            medium_count = int(num_questions * 0.5)
            hard_count = num_questions - easy_count - medium_count
            return [2] * easy_count + [3] * medium_count + [4] * hard_count
        else:
            easy_count = int(num_questions * 0.2)
            medium_count = int(num_questions * 0.4)
            hard_count = num_questions - easy_count - medium_count
            return [2] * easy_count + [3] * medium_count + [4] * hard_count
    
    def _generate_from_template(self, template_data):
        """Generate question from template with random parameters"""
        template = template_data["template"]
        params = template_data["parameters"]
        
        generated_params = {}
        for param, options in params.items():
            generated_params[param] = random.choice(options)
        
        try:
            return template.format(**generated_params)
        except KeyError:
            return template
    
    def _fallback_questions(self, topic):
        """Fallback to static questions if smart generation fails"""
        fallback = {
            "sta": [
                "What is Static Timing Analysis and why is it critical in modern chip design?",
                "Explain setup and hold time violations. How do you debug and fix them?",
                "What is clock skew and how does it impact timing closure?",
                "Describe the concept of timing corners and their importance in analysis.",
                "How do you handle timing analysis for multiple clock domains?",
                "What are timing exceptions and when would you use false paths?",
                "Explain the difference between ideal clock and propagated clock analysis.",
                "What is clock jitter and how do you account for it in timing calculations?",
                "How do you analyze timing for memory interfaces and what makes them special?",
                "What is OCV (On-Chip Variation) and why do you add OCV margins in STA?",
                "Explain multicycle paths and give an example where you would use them.",
                "How do you handle timing analysis for generated clocks and clock dividers?",
                "What is clock domain crossing (CDC) and what timing checks are needed?",
                "Describe timing analysis for high-speed interfaces and their challenges.",
                "What reports do you check for timing signoff and why are they important?",
                "How do you ensure timing correlation between STA tools and silicon?",
                "What is useful skew and how can it help with timing closure?",
                "Explain timing optimization techniques for low-power designs."
            ],
            "cts": [
                "What is Clock Tree Synthesis and what are its main objectives?",
                "Explain different clock tree topologies and when to use each.",
                "How do you optimize clock trees for power consumption?",
                "What is useful skew and how can it help timing closure?",
                "Describe challenges in CTS for high-frequency designs.",
                "What is clock skew and what causes it in clock trees?",
                "How do you handle clock gating cells in clock tree synthesis?",
                "Explain the concept of clock insertion delay and how to minimize it.",
                "What are the trade-offs between H-tree and balanced tree topologies?",
                "How do you handle multiple clock domains in CTS?",
                "What is clock mesh and when would you choose it over tree topology?",
                "Describe clock tree optimization for process variation and yield.",
                "How do you build clock trees for multi-voltage designs?",
                "What is the typical CTS flow and when does it happen in the design cycle?",
                "How do you verify clock tree quality after synthesis?",
                "What are the challenges of clock tree synthesis in advanced nodes?",
                "Explain clock tree balancing and why it's important.",
                "How do you handle clock tree synthesis for low-power designs?"
            ],
            "signoff": [
                "What are the main signoff checks required before tape-out?",
                "Explain DRC violations and systematic approaches to fix them.",
                "What is LVS and how do you debug LVS mismatches?",
                "Describe IR drop analysis and mitigation techniques.",
                "How do you perform timing signoff for multi-corner analysis?",
                "What is antenna checking and why can violations damage your chip?",
                "Explain metal density rules and their impact on manufacturing.",
                "What is electromigration and how do you prevent EM violations?",
                "How do you perform signal integrity analysis during signoff?",
                "What is formal verification and how does it differ from simulation?",
                "Describe the signoff flow for advanced technology nodes.",
                "How do you coordinate signoff across different design teams?",
                "What additional checks are needed for multi-voltage designs?",
                "Explain thermal analysis and its importance in signoff.",
                "What is yield analysis and how do you optimize for manufacturing yield?",
                "How do you validate power delivery networks during signoff?",
                "What are the challenges of signoff in 7nm and below technologies?",
                "Describe the handoff process between design and manufacturing teams."
            ]
        }
        
        base_questions = fallback.get(topic, fallback["sta"])
        extended = []
        for i in range(18):
            base_q = base_questions[i % len(base_questions)]
            if i >= len(base_questions):
                extended.append(f"Advanced: {base_q}")
            else:
                extended.append(base_q)
        return extended

# Enhanced Scoring System
class EnhancedScoringSystem:
    def __init__(self):
        self.scoring_rubrics = {
            "sta": {
                "technical_terms": ["setup", "hold", "slack", "skew", "jitter", "corner", "violation", "closure"],
                "advanced_terms": ["ocv", "cppr", "useful skew", "clock latency", "propagated", "ideal"],
                "methodology_terms": ["debug", "optimize", "analyze", "systematic", "root cause"],
                "weights": {"technical": 0.4, "depth": 0.3, "methodology": 0.2, "clarity": 0.1}
            },
            "cts": {
                "technical_terms": ["clock tree", "skew", "insertion delay", "buffer", "topology", "synthesis"],
                "advanced_terms": ["h-tree", "mesh", "useful skew", "gating", "power optimization"],
                "methodology_terms": ["balance", "optimize", "strategy", "approach", "technique"],
                "weights": {"technical": 0.4, "depth": 0.3, "methodology": 0.2, "clarity": 0.1}
            },
            "signoff": {
                "technical_terms": ["drc", "lvs", "antenna", "density", "ir drop", "em", "signoff"],
                "advanced_terms": ["formal verification", "multi-corner", "yield analysis", "si analysis"],
                "methodology_terms": ["debug", "systematic", "flow", "process", "validation"],
                "weights": {"technical": 0.4, "depth": 0.3, "methodology": 0.2, "clarity": 0.1}
            }
        }
    
    def analyze_answer_comprehensive(self, question, answer, topic):
        """Comprehensive answer analysis with detailed feedback"""
        if not answer or len(answer.strip()) < 20:
            return {
                "score": 0,
                "breakdown": {"technical": 0, "depth": 0, "methodology": 0, "clarity": 0},
                "feedback": "Answer too short or empty",
                "suggestions": ["Provide more detailed technical explanation", "Include specific examples", "Explain methodology"]
            }
        
        rubric = self.scoring_rubrics.get(topic, self.scoring_rubrics["sta"])
        answer_lower = answer.lower()
        word_count = len(answer.split())
        
        # Technical accuracy score
        technical_score = self._score_technical_content(answer_lower, rubric)
        
        # Depth and detail score
        depth_score = self._score_depth(answer, word_count)
        
        # Methodology score
        methodology_score = self._score_methodology(answer_lower, rubric)
        
        # Clarity and structure score
        clarity_score = self._score_clarity(answer)
        
        # Weighted final score
        weights = rubric["weights"]
        final_score = (
            technical_score * weights["technical"] +
            depth_score * weights["depth"] +
            methodology_score * weights["methodology"] +
            clarity_score * weights["clarity"]
        ) * 10
        
        # Generate feedback and suggestions
        feedback, suggestions = self._generate_feedback(
            technical_score, depth_score, methodology_score, clarity_score, word_count
        )
        
        return {
            "score": round(final_score, 1),
            "breakdown": {
                "technical": round(technical_score * 10, 1),
                "depth": round(depth_score * 10, 1),
                "methodology": round(methodology_score * 10, 1),
                "clarity": round(clarity_score * 10, 1)
            },
            "feedback": feedback,
            "suggestions": suggestions,
            "word_count": word_count
        }
    
    def _score_technical_content(self, answer_lower, rubric):
        tech_terms = sum(1 for term in rubric["technical_terms"] if term in answer_lower)
        advanced_terms = sum(1 for term in rubric["advanced_terms"] if term in answer_lower)
        
        tech_score = min(tech_terms / 3, 1.0)
        advanced_score = min(advanced_terms / 2, 0.5)
        
        return min(tech_score + advanced_score, 1.0)
    
    def _score_depth(self, answer, word_count):
        word_score = min(word_count / 100, 0.7)
        
        has_examples = any(marker in answer.lower() for marker in ['example', 'for instance', 'such as'])
        has_numbers = bool(re.search(r'\d+', answer))
        has_comparisons = any(marker in answer.lower() for marker in ['compare', 'versus', 'vs', 'better', 'worse'])
        
        structure_score = (has_examples * 0.1) + (has_numbers * 0.1) + (has_comparisons * 0.1)
        
        return min(word_score + structure_score, 1.0)
    
    def _score_methodology(self, answer_lower, rubric):
        method_terms = sum(1 for term in rubric["methodology_terms"] if term in answer_lower)
        
        has_steps = any(marker in answer_lower for marker in ['step', 'first', 'second', 'then', 'next', 'finally'])
        has_process = any(marker in answer_lower for marker in ['process', 'flow', 'procedure', 'approach'])
        
        method_score = min(method_terms / 2, 0.7)
        process_score = (has_steps * 0.15) + (has_process * 0.15)
        
        return min(method_score + process_score, 1.0)
    
    def _score_clarity(self, answer):
        sentences = answer.split('.')
        avg_sentence_length = sum(len(s.split()) for s in sentences) / max(len(sentences), 1)
        
        length_score = 1.0 - abs(avg_sentence_length - 17.5) / 17.5
        length_score = max(0, min(length_score, 1.0))
        
        has_organization = any(marker in answer.lower() for marker in [':', '-', '1.', '2.', 'bullet'])
        org_score = 0.3 if has_organization else 0
        
        return min(length_score * 0.7 + org_score, 1.0)
    
    def _generate_feedback(self, tech_score, depth_score, method_score, clarity_score, word_count):
        feedback_parts = []
        suggestions = []
        
        if tech_score >= 0.8:
            feedback_parts.append("Strong technical knowledge demonstrated")
        elif tech_score >= 0.6:
            feedback_parts.append("Good technical understanding shown")
            suggestions.append("Include more specific technical terminology")
        else:
            feedback_parts.append("Limited technical content")
            suggestions.append("Use more industry-specific technical terms")
        
        if depth_score >= 0.8:
            feedback_parts.append("comprehensive analysis provided")
        elif depth_score >= 0.6:
            feedback_parts.append("adequate detail level")
            suggestions.append("Provide more detailed explanations and examples")
        else:
            feedback_parts.append("needs more depth")
            suggestions.append("Expand with specific examples and quantitative details")
        
        if method_score >= 0.7:
            feedback_parts.append("clear methodology described")
        else:
            feedback_parts.append("methodology could be clearer")
            suggestions.append("Describe step-by-step approach or process")
        
        if word_count < 50:
            suggestions.append("Increase answer length for better coverage")
        elif word_count > 300:
            suggestions.append("Consider more concise explanations")
        
        feedback = ", ".join(feedback_parts).capitalize() + f" ({word_count} words)"
        
        return feedback, suggestions

# Initialize components
DatabaseManager.init_db()
question_generator = SmartQuestionGenerator()
scoring_system = EnhancedScoringSystem()

# User authentication functions
def hash_pass(pwd):
    return hashlib.sha256(pwd.encode()).hexdigest()

def check_pass(hashed, pwd):
    return hashed == hashlib.sha256(pwd.encode()).hexdigest()

def init_data():
    """Initialize demo data"""
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    # Check if admin exists
    c.execute('SELECT id FROM users WHERE id = ?', ('admin',))
    if not c.fetchone():
        # Create admin
        c.execute("""
            INSERT INTO users (id, username, display_name, email, password, is_admin, experience, created_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, ('admin', 'admin', 'System Administrator', 'admin@vibhuayu.com', 
              hash_pass('Vibhuaya@3006'), 1, 5, datetime.now().isoformat()))
        
        # Create 18 engineers
        engineer_data = [
            ('eng001', 'Kranthi', 'kranthi@vibhuayu.com', 3),
            ('eng002', 'Neela', 'neela@vibhuayu.com', 4),
            ('eng003', 'Bhanu', 'bhanu@vibhuayu.com', 2),
            ('eng004', 'Lokeshwari', 'lokeshwari@vibhuayu.com', 5),
            ('eng005', 'Nagesh', 'nagesh@vibhuayu.com', 3),
            ('eng006', 'VJ', 'vj@vibhuayu.com', 4),
            ('eng007', 'Pravalika', 'pravalika@vibhuayu.com', 2),
            ('eng008', 'Daniel', 'daniel@vibhuayu.com', 6),
            ('eng009', 'Karthik', 'karthik@vibhuayu.com', 3),
            ('eng010', 'Hema', 'hema@vibhuayu.com', 4),
            ('eng011', 'Naveen', 'naveen@vibhuayu.com', 5),
            ('eng012', 'Srinivas', 'srinivas@vibhuayu.com', 3),
            ('eng013', 'Meera', 'meera@vibhuayu.com', 2),
            ('eng014', 'Suraj', 'suraj@vibhuayu.com', 4),
            ('eng015', 'Akhil', 'akhil@vibhuayu.com', 3),
            ('eng016', 'Vikas', 'vikas@vibhuayu.com', 5),
            ('eng017', 'Sahith', 'sahith@vibhuayu.com', 2),
            ('eng018', 'Sravan', 'sravan@vibhuayu.com', 4)
        ]
        
        for uid, name, email, exp in engineer_data:
            c.execute("""
                INSERT INTO users (id, username, display_name, email, password, is_admin, experience, department, created_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (uid, uid, name, email, hash_pass('password123'), 0, exp, 'Physical Design', datetime.now().isoformat()))
    
    conn.commit()
    conn.close()

def _time_ago(date_str):
    """Calculate time ago from date string"""
    try:
        date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        now = datetime.now()
        diff = now - date_obj
        
        if diff.days > 0:
            return f"{diff.days}d ago"
        elif diff.seconds > 3600:
            return f"{diff.seconds // 3600}h ago"
        elif diff.seconds > 60:
            return f"{diff.seconds // 60}m ago"
        else:
            return "Just now"
    except:
        return "Unknown"

# Routes
@app.route('/')
def home():
    if 'user_id' in session:
        if session.get('is_admin'):
            return redirect('/admin')
        return redirect('/student')
    return redirect('/login')

@app.route('/health')
def health():
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE username = ?', (username,))
        user = c.fetchone()
        conn.close()
        
        if user and check_pass(user[4], password):
            session['user_id'] = user[0]
            session['username'] = user[1]
            session['display_name'] = user[2]
            session['is_admin'] = bool(user[5])
            session['theme'] = user[10] if user[10] else 'light'
            
            # Update last login
            conn = sqlite3.connect(DATABASE)
            c = conn.cursor()
            c.execute('UPDATE users SET last_login = ? WHERE id = ?', 
                     (datetime.now().isoformat(), user[0]))
            conn.commit()
            conn.close()
            
            # Log analytics
            DatabaseManager.log_analytics('login', user[0])
            
            if bool(user[5]):
                return redirect('/admin')
            return redirect('/student')
    
    # Enhanced login page
    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
    <title>Vibhuayu Technologies - Enhanced PD Assessment</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        :root {
            --primary-color: #667eea;
            --secondary-color: #764ba2;
            --success-color: #10b981;
            --warning-color: #f59e0b;
            --error-color: #ef4444;
            --bg-primary: #0f172a;
            --bg-secondary: #1e293b;
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --surface: rgba(255, 255, 255, 0.98);
            --border: #e2e8f0;
        }
        
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            background: linear-gradient(135deg, var(--bg-primary) 0%, var(--bg-secondary) 100%); 
            min-height: 100vh; 
            display: flex; 
            align-items: center; 
            justify-content: center; 
            position: relative;
            overflow-x: hidden;
        }
        
        body::before {
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0; bottom: 0;
            background: 
                radial-gradient(circle at 30% 40%, rgba(102, 126, 234, 0.3) 0%, transparent 50%),
                radial-gradient(circle at 80% 80%, rgba(118, 75, 162, 0.15) 0%, transparent 50%);
            z-index: 1;
        }
        
        .container {
            position: relative; z-index: 2;
            background: var(--surface);
            backdrop-filter: blur(20px);
            border-radius: 24px;
            padding: 50px 40px;
            width: min(450px, 90vw);
            box-shadow: 0 25px 50px rgba(0, 0, 0, 0.25);
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        .logo-section {
            text-align: center;
            margin-bottom: 35px;
        }
        
        .logo {
            width: 80px; height: 80px;
            margin: 0 auto 20px;
            background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
            border-radius: 20px;
            display: flex; align-items: center; justify-content: center;
            color: white; font-size: 36px; font-weight: 900;
            box-shadow: 0 10px 30px rgba(102, 126, 234, 0.3);
            position: relative; overflow: hidden;
        }
