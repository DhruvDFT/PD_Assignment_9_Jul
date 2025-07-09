# Enhanced PD Assessment System with Advanced Features
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
        
        # Question pools table (for smart generation)
        c.execute("""
            CREATE TABLE IF NOT EXISTS question_pools (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic TEXT,
                difficulty INTEGER,
                template TEXT,
                parameters TEXT,
                usage_count INTEGER DEFAULT 0,
                effectiveness_score REAL DEFAULT 0.0
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
                    "focus": ["timing_analysis", "problem_solving"],
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
                    "focus": ["concepts", "industry_knowledge"],
                    "parameters": {
                        "concept": ["clock jitter", "OCV", "useful skew", "clock latency", "timing corners"],
                        "impact_area": ["setup timing", "hold timing", "power consumption", "area optimization"],
                        "technology_node": ["7nm", "5nm", "3nm", "advanced nodes"]
                    }
                },
                {
                    "template": "You're analyzing a {design_type} with {num_domains} clock domains running at different frequencies ({freq_list}). Describe your approach to handle clock domain crossings and ensure timing closure across all interfaces.",
                    "difficulty": 4,
                    "focus": ["multi_domain", "advanced_concepts"],
                    "parameters": {
                        "design_type": ["SoC", "CPU", "GPU", "AI accelerator"],
                        "num_domains": [3, 4, 5, 6],
                        "freq_list": ["100MHz/500MHz/1GHz", "200MHz/800MHz/1.5GHz", "50MHz/1GHz/2GHz"]
                    }
                }
            ],
            "cts": [
                {
                    "template": "Design a clock tree for a {design_size} design with {num_flops} flip-flops distributed across {die_size}. The target skew is {target_skew}ps and you have {buffer_types} buffer types available. Explain your tree topology choice and optimization strategy.",
                    "difficulty": 3,
                    "focus": ["tree_design", "optimization"],
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
                    "focus": ["power_optimization", "constraints"],
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
                    "focus": ["debugging", "project_management"],
                    "parameters": {
                        "check_type": ["DRC", "LVS", "Antenna", "Metal Density"],
                        "num_violations": [50, 100, 200, 500],
                        "violation_dist": ["70% spacing, 20% width, 10% via", "50% density, 30% spacing, 20% antenna", "60% LVS nets, 25% devices, 15% properties"]
                    }
                },
                {
                    "template": "Perform signoff analysis for a {design_type} in {technology} process. The design has {power_domains} power domains and {io_count} I/Os. List all required signoff checks and create a verification plan with timeline and responsibilities.",
                    "difficulty": 4,
                    "focus": ["signoff_flow", "planning"],
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
            # Junior: 60% easy, 30% medium, 10% hard
            easy_count = int(num_questions * 0.6)
            medium_count = int(num_questions * 0.3)
            hard_count = num_questions - easy_count - medium_count
            return [2] * easy_count + [3] * medium_count + [4] * hard_count
        elif engineer_exp <= 4:
            # Mid: 30% easy, 50% medium, 20% hard
            easy_count = int(num_questions * 0.3)
            medium_count = int(num_questions * 0.5)
            hard_count = num_questions - easy_count - medium_count
            return [2] * easy_count + [3] * medium_count + [4] * hard_count
        else:
            # Senior: 20% easy, 40% medium, 40% hard
            easy_count = int(num_questions * 0.2)
            medium_count = int(num_questions * 0.4)
            hard_count = num_questions - easy_count - medium_count
            return [2] * easy_count + [3] * medium_count + [4] * hard_count
    
    def _generate_from_template(self, template_data):
        """Generate question from template with random parameters"""
        template = template_data["template"]
        params = template_data["parameters"]
        
        # Generate random parameters
        generated_params = {}
        for param, options in params.items():
            generated_params[param] = random.choice(options)
        
        try:
            return template.format(**generated_params)
        except KeyError:
            return template  # Return template as-is if parameter missing
    
    def _fallback_questions(self, topic):
        """Fallback to static questions if smart generation fails"""
        fallback = {
            "sta": [
                "What is Static Timing Analysis and why is it critical in modern chip design?",
                "Explain setup and hold time violations. How do you debug and fix them?",
                "What is clock skew and how does it impact timing closure?",
                "Describe the concept of timing corners and their importance in analysis.",
                "How do you handle timing analysis for multiple clock domains?"
            ],
            "cts": [
                "What is Clock Tree Synthesis and what are its main objectives?",
                "Explain different clock tree topologies and when to use each.",
                "How do you optimize clock trees for power consumption?",
                "What is useful skew and how can it help timing closure?",
                "Describe challenges in CTS for high-frequency designs."
            ],
            "signoff": [
                "What are the main signoff checks required before tape-out?",
                "Explain DRC violations and systematic approaches to fix them.",
                "What is LVS and how do you debug LVS mismatches?",
                "Describe IR drop analysis and mitigation techniques.",
                "How do you perform timing signoff for multi-corner analysis?"
            ]
        }
        
        base_questions = fallback.get(topic, fallback["sta"])
        # Extend to 18 questions by repeating and modifying
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
        ) * 10  # Scale to 10
        
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
        """Score technical term usage"""
        tech_terms = sum(1 for term in rubric["technical_terms"] if term in answer_lower)
        advanced_terms = sum(1 for term in rubric["advanced_terms"] if term in answer_lower)
        
        # Normalize scores
        tech_score = min(tech_terms / 3, 1.0)  # Up to 3 technical terms = full score
        advanced_score = min(advanced_terms / 2, 0.5)  # Up to 2 advanced terms = bonus
        
        return min(tech_score + advanced_score, 1.0)
    
    def _score_depth(self, answer, word_count):
        """Score depth and detail level"""
        # Word count component
        word_score = min(word_count / 100, 0.7)  # 100+ words = 70% of depth score
        
        # Structure indicators
        has_examples = any(marker in answer.lower() for marker in ['example', 'for instance', 'such as'])
        has_numbers = bool(re.search(r'\d+', answer))
        has_comparisons = any(marker in answer.lower() for marker in ['compare', 'versus', 'vs', 'better', 'worse'])
        
        structure_score = (has_examples * 0.1) + (has_numbers * 0.1) + (has_comparisons * 0.1)
        
        return min(word_score + structure_score, 1.0)
    
    def _score_methodology(self, answer_lower, rubric):
        """Score methodology and approach"""
        method_terms = sum(1 for term in rubric["methodology_terms"] if term in answer_lower)
        
        # Look for step-by-step approach
        has_steps = any(marker in answer_lower for marker in ['step', 'first', 'second', 'then', 'next', 'finally'])
        has_process = any(marker in answer_lower for marker in ['process', 'flow', 'procedure', 'approach'])
        
        method_score = min(method_terms / 2, 0.7)  # Up to 2 methodology terms
        process_score = (has_steps * 0.15) + (has_process * 0.15)
        
        return min(method_score + process_score, 1.0)
    
    def _score_clarity(self, answer):
        """Score clarity and organization"""
        sentences = answer.split('.')
        avg_sentence_length = sum(len(s.split()) for s in sentences) / max(len(sentences), 1)
        
        # Prefer moderate sentence length (10-25 words)
        length_score = 1.0 - abs(avg_sentence_length - 17.5) / 17.5
        length_score = max(0, min(length_score, 1.0))
        
        # Check for organization markers
        has_organization = any(marker in answer.lower() for marker in [':', '-', '1.', '2.', 'bullet'])
        org_score = 0.3 if has_organization else 0
        
        return min(length_score * 0.7 + org_score, 1.0)
    
    def _generate_feedback(self, tech_score, depth_score, method_score, clarity_score, word_count):
        """Generate detailed feedback and suggestions"""
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
        
        if user and check_pass(user[4], password):  # password is at index 4
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
            
            if bool(user[5]):  # is_admin
                return redirect('/admin')
            return redirect('/student')
    
    # Enhanced login page with theme toggle
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

# Enhanced Admin Dashboard with Analytics
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
        time_ago = _time_ago(sub[4])  # submitted_date
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
                <a href="/admin/quick-view/{sub[1]}" class="quick-btn">Quick View</a>
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
        
        .review-btn, .quick-btn {
            padding: 8px 16px; text-decoration: none;
            border-radius: 8px; font-weight: 600;
            font-size: 14px; transition: all 0.3s ease;
        }
        
        .review-btn {
            background: linear-gradient(135deg, var(--success), #059669);
            color: white;
        }
        
        .quick-btn {
            background: rgba(102, 126, 234, 0.1);
            color: var(--primary);
        }
        
        .review-btn:hover, .quick-btn:hover {
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
        
        .topic-badge {
            background: var(--primary); color: white;
            padding: 4px 12px; border-radius: 20px;
            font-size: 12px; font-weight: 600;
            text-transform: uppercase;
        }
        
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
                <a href="/admin/bulk-create" class="nav-btn">⚡ Bulk Create</a>
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
                        <span class="topic-badge">{{ stat.topic.upper() }}</span>
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
                // Could show adaptive difficulty preview here
            }
        });
        
        // Auto-refresh pending count every 30 seconds
        setInterval(() => {
            fetch('/admin/stats')
                .then(response => response.json())
                .then(data => {
                    // Update stats if needed
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

# Continue with more routes...
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

# Railway compatibility
application = app

if __name__ == '__main__':
    try:
        print("🚀 Starting Enhanced Railway Flask App...")
        init_data()
        print("✅ Database and demo data initialized")
        
        port = int(os.environ.get('PORT', 5000))
        print(f"✅ Starting server on port {port}")
        
        app.run(host='0.0.0.0', port=port, debug=False)
        
    except Exception as e:
        print(f"❌ STARTUP ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        exit(1)
