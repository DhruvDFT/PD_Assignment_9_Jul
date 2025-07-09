# app.py (Updated with Railway compatibility)
import os
import hashlib
from datetime import datetime, timedelta
from flask import Flask, request, redirect, session

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'pd-secret-key')

# Global data
users = {}
assignments = {}
counter = 0

def hash_pass(pwd):
    return hashlib.sha256(pwd.encode()).hexdigest()

def check_pass(hashed, pwd):
    return hashed == hashlib.sha256(pwd.encode()).hexdigest()

def init_data():
    global users
    users['admin'] = {
        'id': 'admin',
        'username': 'admin',
        'password': hash_pass('Vibhuaya@3006'),
        'is_admin': True,
        'exp': 5
    }
    
    # 18 Individual Engineers
    engineer_data = [
        ('eng001', 'Kranthi'),
        ('eng002', 'Neela'),
        ('eng003', 'Bhanu'),
        ('eng004', 'Lokeshwari'),
        ('eng005', 'Nagesh'),
        ('eng006', 'VJ'),
        ('eng007', 'Pravalika'),
        ('eng008', 'Daniel'),
        ('eng009', 'Karthik'),
        ('eng010', 'Hema'),
        ('eng011', 'Naveen'),
        ('eng012', 'Srinivas'),
        ('eng013', 'Meera'),
        ('eng014', 'Suraj'),
        ('eng015', 'Akhil'),
        ('eng016', 'Vikas'),
        ('eng017', 'Sahith'),
        ('eng018', 'Sravan')
    ]
    
    for uid, display_name in engineer_data:
        users[uid] = {
            'id': uid,
            'username': uid,
            'display_name': display_name,
            'password': hash_pass('password123'),
            'is_admin': False,
            'exp': 3 + (int(uid[-2:]) % 4)
        }

# Simple Questions - 18 per topic (2+ Experience Level)
QUESTIONS = {
    "sta": [
        "What is Static Timing Analysis (STA)? Why is it important in chip design?",
        "Explain setup time and hold time. What happens when these requirements are violated?",
        "What is slack? How do you calculate setup slack and hold slack?",
        "Your design has setup violations of -30ps. List 3 methods to fix these violations.",
        "What is clock skew? How does it affect setup and hold timing?",
        "Explain timing corners. Which corners do you use for setup and hold analysis?",
        "What are timing exceptions? When would you use false paths?",
        "Describe the difference between ideal clock and propagated clock analysis.",
        "What is clock jitter? How do you account for it in timing calculations?",
        "Your hold violations are at 25ps. What are the common ways to fix hold violations?",
        "What is OCV (On-Chip Variation)? Why do you add OCV margins in STA?",
        "Explain multicycle paths. Give an example where you would use them.",
        "How do you analyze timing for multiple clock domains?",
        "What is clock domain crossing (CDC)? What timing checks are needed?",
        "Describe timing analysis for memory interfaces (SRAM). What makes it different?",
        "What reports do you check for timing signoff? List the key timing reports.",
        "How do you handle timing analysis for generated clocks?",
        "What is timing correlation? How do you ensure STA matches real silicon performance?"
    ],
    
    "cts": [
        "What is Clock Tree Synthesis (CTS)? Why do we build clock trees?",
        "What is clock skew? What is an acceptable skew target for most designs?",
        "Explain clock insertion delay. How is it different from clock skew?",
        "Your clock tree has 150ps skew but target is 50ps. How would you reduce it?",
        "What elements are used to build clock trees? Describe buffers and inverters.",
        "What is clock tree balancing? How do you achieve balanced insertion delay?",
        "What is useful skew? Give an example where you would use it intentionally.",
        "How do clock gating cells affect your clock tree? Where do you place them?",
        "Compare H-tree vs balanced tree topologies. When would you use each?",
        "Your design has 3 clock domains. How do you handle multiple clocks in CTS?",
        "What techniques can you use to reduce clock tree power consumption?",
        "How do you build clock trees when you have multiple voltage domains?",
        "What is clock mesh? When would you choose mesh over tree topology?",
        "Describe CTS challenges for high-frequency designs (>1GHz).",
        "How do you handle CTS for designs with power gating?",
        "What is the typical flow sequence? When does CTS happen relative to placement and routing?",
        "How do you optimize clock trees for process variation and yield?",
        "What reports do you check after CTS? How do you verify clock tree quality?"
    ],
    
    "signoff": [
        "What is signoff in chip design? What must pass before tape-out?",
        "List 5 major signoff checks. Why is each one important?",
        "What is DRC (Design Rule Check)? Give 3 examples of common DRC violations.",
        "What is LVS (Layout vs Schematic)? What does an LVS mismatch mean?",
        "Your design has 20 LVS errors. What systematic approach would you use to debug them?",
        "What is antenna checking? Why can antenna violations damage your chip?",
        "Explain metal density rules. What happens if density is too low?",
        "What is IR drop analysis? What are typical IR drop limits?",
        "Your design has IR drop violations of 120mV. How would you fix them?",
        "What is electromigration (EM)? How do you prevent EM violations?",
        "Describe timing signoff. What timing reports are required?",
        "What is signal integrity (SI) analysis? What SI effects do you check?",
        "How do you perform power analysis for signoff? What power metrics matter?",
        "What additional checks are needed for multi-voltage designs?",
        "What is formal verification? How is it different from simulation?",
        "Explain thermal analysis. How do you ensure your chip won't overheat?",
        "What is yield analysis? How do you optimize for manufacturing yield?",
        "Describe the typical signoff flow. Who signs off on what?"
    ]
}

def analyze_answer_quality(question, answer, topic):
    """Analyzes answer quality and suggests a score"""
    if not answer or len(answer.strip()) < 20:
        return 0, "Answer too short or empty"
    
    answer_lower = answer.lower()
    
    # Define scoring criteria for each topic
    scoring_criteria = {
        'sta': {
            'excellent_terms': ['setup time', 'hold time', 'slack', 'timing violation', 'clock skew', 'timing corner', 'propagated clock', 'jitter', 'ocv'],
            'good_terms': ['timing', 'clock', 'delay', 'path', 'constraint', 'analysis', 'signoff', 'violation'],
            'methodology_terms': ['systematic', 'approach', 'method', 'technique', 'optimization', 'analysis']
        },
        'cts': {
            'excellent_terms': ['clock tree', 'skew', 'insertion delay', 'balancing', 'useful skew', 'clock gating', 'h-tree', 'clock mesh', 'power optimization'],
            'good_terms': ['clock', 'tree', 'buffer', 'delay', 'synthesis', 'distribution', 'domain', 'topology'],
            'methodology_terms': ['optimization', 'technique', 'approach', 'method', 'strategy', 'implementation']
        },
        'signoff': {
            'excellent_terms': ['drc', 'lvs', 'antenna', 'ir drop', 'electromigration', 'metal density', 'signal integrity', 'formal verification'],
            'good_terms': ['signoff', 'verification', 'check', 'violation', 'analysis', 'tape-out', 'design rule'],
            'methodology_terms': ['systematic', 'debug', 'approach', 'method', 'flow', 'process']
        }
    }
    
    criteria = scoring_criteria.get(topic, scoring_criteria['sta'])
    
    # Count relevant technical terms
    excellent_count = sum(1 for term in criteria['excellent_terms'] if term in answer_lower)
    good_count = sum(1 for term in criteria['good_terms'] if term in answer_lower)
    methodology_count = sum(1 for term in criteria['methodology_terms'] if term in answer_lower)
    
    # Calculate base score
    word_count = len(answer.split())
    has_structure = any(marker in answer_lower for marker in ['1.', '2.', 'first', 'second', 'step'])
    
    # Scoring logic
    if excellent_count >= 3 and word_count >= 80:
        base_score = 8
        reasoning = f"Strong technical content ({excellent_count} advanced terms)"
    elif excellent_count >= 2 and word_count >= 50:
        base_score = 7
        reasoning = f"Good technical knowledge ({excellent_count} advanced terms)"
    elif excellent_count >= 1 or good_count >= 3:
        base_score = 6
        reasoning = f"Adequate technical understanding"
    elif good_count >= 2 and word_count >= 30:
        base_score = 5
        reasoning = f"Basic technical knowledge"
    else:
        base_score = 4
        reasoning = "Limited technical content"
    
    # Bonus points
    if methodology_count >= 1:
        base_score += 1
        reasoning += " + methodology"
    if has_structure:
        base_score += 0.5
        reasoning += " + structured"
    
    final_score = min(10, round(base_score))
    reasoning += f" ({word_count} words)"
    
    return final_score, reasoning

def create_test(eng_id, topic):
    global counter
    counter += 1
    test_id = f"PD_{topic}_{eng_id}_{counter}"
    
    # Each engineer gets all 18 questions from their topic
    selected_questions = QUESTIONS[topic]
    
    test = {
        'id': test_id,
        'engineer_id': eng_id,
        'topic': topic,
        'questions': selected_questions,
        'answers': {},
        'status': 'pending',
        'created': datetime.now().isoformat(),
        'due': (datetime.now() + timedelta(days=3)).isoformat(),
        'score': None,
        'auto_scores': {}
    }
    
    assignments[test_id] = test
    return test

@app.route('/')
def home():
    if 'user_id' in session:
        if session.get('is_admin'):
            return redirect('/admin')
        return redirect('/student')
    return redirect('/login')

@app.route('/health')
def health():
    return 'OK'

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        user = users.get(username)
        if user and check_pass(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['is_admin'] = user.get('is_admin', False)
            
            if user.get('is_admin'):
                return redirect('/admin')
            return redirect('/student')
    
    return '''
<!DOCTYPE html>
<html>
<head>
    <title>Vibhuayu Technologies - PD Assessment</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            background: linear-gradient(135deg, #0f0f23 0%, #1a1a2e 50%, #16213e 100%); 
            min-height: 100vh; 
            display: flex; 
            align-items: center; 
            justify-content: center; 
        }
        .container {
            background: rgba(255, 255, 255, 0.98);
            border-radius: 24px;
            padding: 50px 40px;
            width: 450px;
            box-shadow: 0 25px 50px rgba(0, 0, 0, 0.25);
        }
        .logo {
            width: 80px;
            height: 80px;
            margin: 0 auto 20px;
            background: linear-gradient(135deg, #2563eb, #7c3aed, #db2777);
            border-radius: 20px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 36px;
            font-weight: 900;
        }
        .title {
            font-size: 28px;
            font-weight: 700;
            text-align: center;
            margin-bottom: 8px;
        }
        .subtitle {
            color: #64748b;
            font-size: 16px;
            text-align: center;
            margin-bottom: 35px;
        }
        .form-group {
            margin-bottom: 24px;
        }
        .form-group label {
            display: block;
            margin-bottom: 8px;
            color: #374151;
            font-weight: 600;
        }
        .form-input {
            width: 100%;
            padding: 16px 20px;
            border: 2px solid #e5e7eb;
            border-radius: 12px;
            font-size: 16px;
        }
        .form-input:focus {
            outline: none;
            border-color: #3b82f6;
        }
        .login-btn {
            width: 100%;
            padding: 16px;
            background: linear-gradient(135deg, #3b82f6, #1d4ed8);
            color: white;
            border: none;
            border-radius: 12px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            margin-bottom: 30px;
        }
        .info-card {
            background: #f8fafc;
            border-radius: 16px;
            padding: 24px;
            text-align: center;
        }
        .credentials {
            background: white;
            border-radius: 8px;
            padding: 12px;
            margin: 12px 0;
            border-left: 4px solid #3b82f6;
        }
        .eng-list {
            font-size: 12px;
            color: #64748b;
            line-height: 1.6;
            margin-top: 12px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="logo">V7</div>
        <div class="title">PD Assessment Portal</div>
        <div class="subtitle">Physical Design Evaluation System</div>
        
        <form method="POST">
            <div class="form-group">
                <label>Username</label>
                <input type="text" name="username" class="form-input" placeholder="Enter your username" required>
            </div>
            <div class="form-group">
                <label>Password</label>
                <input type="password" name="password" class="form-input" placeholder="Enter your password" required>
            </div>
            <button type="submit" class="login-btn">Access Assessment Portal</button>
        </form>
        
        <div class="info-card">
            <div style="font-weight: 700; margin-bottom: 16px;">🔐 Test Credentials</div>
            <div class="credentials">
                <strong>Engineers:</strong> eng001 through eng018<br>
                <strong>Password:</strong> password123
            </div>
            <div class="eng-list">
                <strong>18 Engineers:</strong><br>
                Kranthi • Neela • Bhanu • Lokeshwari • Nagesh • VJ<br>
                Pravalika • Daniel • Karthik • Hema • Naveen • Srinivas<br>
                Meera • Suraj • Akhil • Vikas • Sahith • Sravan
            </div>
        </div>
    </div>
</body>
</html>'''

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

@app.route('/admin')
def admin():
    if not session.get('is_admin'):
        return redirect('/login')
    
    engineers = [u for u in users.values() if not u.get('is_admin')]
    all_tests = list(assignments.values())
    pending = [a for a in all_tests if a['status'] == 'submitted']
    
    eng_options = ''
    for eng in engineers:
        display_name = eng.get('display_name', eng['username'])
        eng_options += f'<option value="{eng["id"]}">{display_name} (2+ Experience)</option>'
    
    return f'''
<!DOCTYPE html>
<html>
<head>
    <title>Admin Dashboard</title>
    <style>
        body {{ font-family: Arial; background: #f5f5f5; margin: 0; }}
        .header {{ background: #2563eb; color: white; padding: 20px; }}
        .container {{ max-width: 1200px; margin: 20px auto; padding: 0 20px; }}
        .card {{ background: white; border-radius: 12px; padding: 30px; margin: 20px 0; }}
        .stats {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; }}
        .stat {{ background: white; padding: 20px; border-radius: 12px; text-align: center; }}
        .stat-num {{ font-size: 24px; font-weight: bold; color: #2563eb; }}
        select, button {{ padding: 12px; border: 1px solid #ddd; border-radius: 6px; margin: 5px; }}
        .btn-primary {{ background: #2563eb; color: white; border: none; cursor: pointer; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Admin Dashboard</h1>
        <a href="/logout" style="color: white; float: right;">Logout</a>
    </div>
    
    <div class="container">
        <div class="stats">
            <div class="stat"><div class="stat-num">{len(engineers)}</div><div>Engineers</div></div>
            <div class="stat"><div class="stat-num">{len(all_tests)}</div><div>Tests</div></div>
            <div class="stat"><div class="stat-num">{len(pending)}</div><div>Pending</div></div>
            <div class="stat"><div class="stat-num">54</div><div>Questions</div></div>
        </div>
        
        <div class="card">
            <h2>Create Assessment</h2>
            <form method="POST" action="/admin/create">
                <select name="engineer_id" required>
                    <option value="">Select Engineer...</option>
                    {eng_options}
                </select>
                <select name="topic" required>
                    <option value="">Select Topic...</option>
                    <option value="sta">STA (Static Timing Analysis)</option>
                    <option value="cts">CTS (Clock Tree Synthesis)</option>
                    <option value="signoff">Signoff Checks</option>
                </select>
                <button type="submit" class="btn-primary">Create Assessment</button>
            </form>
        </div>
    </div>
</body>
</html>'''

@app.route('/admin/create', methods=['POST'])
def admin_create():
    if not session.get('is_admin'):
        return redirect('/login')
    
    eng_id = request.form.get('engineer_id')
    topic = request.form.get('topic')
    
    if eng_id and topic and topic in QUESTIONS:
        create_test(eng_id, topic)
    
    return redirect('/admin')

@app.route('/student')
def student():
    if not session.get('user_id') or session.get('is_admin'):
        return redirect('/login')
    
    user_id = session['user_id']
    user = users.get(user_id, {})
    my_tests = [a for a in assignments.values() if a['engineer_id'] == user_id]
    
    # Build tests HTML
    tests_html = ''
    for test in my_tests:
        status = test['status']
        if status == 'completed':
            tests_html += f'''
            <div class="test-card completed">
                <h3>📊 {test["topic"].upper()} Assessment</h3>
                <div class="test-meta">✅ Completed | Score: {test.get("score", 0)}/180 points</div>
                <div class="test-status completed-status">Assessment Completed</div>
            </div>'''
        elif status == 'submitted':
            tests_html += f'''
            <div class="test-card submitted">
                <h3>📝 {test["topic"].upper()} Assessment</h3>
                <div class="test-meta">⏳ Under Review | 18 Questions | Due: {test["due"][:10]}</div>
                <div class="test-status review-status">Awaiting Results</div>
            </div>'''
        else:
            tests_html += f'''
            <div class="test-card pending">
                <h3>🎯 {test["topic"].upper()} Assessment</h3>
                <div class="test-meta">📋 18 Questions | ⏰ Due: {test["due"][:10]} | 🎖️ Max: 180 points</div>
                <a href="/student/test/{test["id"]}" class="start-btn">Start Assessment</a>
            </div>'''
    
    if not tests_html:
        tests_html = '''
        <div class="no-tests">
            <h3>📭 No Assessments Assigned</h3>
            <p>Your administrator will assign assessments soon. Check back later!</p>
        </div>'''
    
    return f'''
<!DOCTYPE html>
<html>
<head>
    <title>Engineer Dashboard - {user.get('display_name', user_id)}</title>
    <style>
        body {{ 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
            margin: 0; 
            min-height: 100vh;
        }}
        .header {{ 
            background: rgba(255,255,255,0.15); 
            backdrop-filter: blur(10px);
            color: white; 
            padding: 20px 0;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
        }}
        .header-content {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .header h1 {{ margin: 0; font-size: 28px; }}
        .logout {{ 
            background: rgba(255,255,255,0.2); 
            color: white; 
            padding: 10px 20px; 
            text-decoration: none; 
            border-radius: 8px;
            transition: all 0.3s ease;
        }}
        .logout:hover {{ background: rgba(255,255,255,0.3); }}
        .container {{ 
            max-width: 1200px; 
            margin: 30px auto; 
            padding: 0 20px; 
        }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .stat {{
            background: rgba(255,255,255,0.95);
            padding: 25px;
            border-radius: 16px;
            text-align: center;
            box-shadow: 0 8px 25px rgba(0,0,0,0.1);
        }}
        .stat-num {{ 
            font-size: 32px; 
            font-weight: 800; 
            color: #667eea; 
            margin-bottom: 5px;
        }}
        .stat-label {{ 
            color: #64748b; 
            font-weight: 600; 
            font-size: 14px;
        }}
        .section {{
            background: rgba(255,255,255,0.95);
            border-radius: 20px;
            padding: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }}
        .section h2 {{
            color: #1e293b;
            margin-bottom: 25px;
            font-size: 24px;
        }}
        .test-card {{
            background: linear-gradient(135deg, #f8fafc, #f1f5f9);
            border-radius: 12px;
            padding: 25px;
            margin: 20px 0;
            border-left: 5px solid #667eea;
            transition: transform 0.3s ease;
        }}
        .test-card:hover {{ transform: translateY(-2px); }}
        .test-card h3 {{ 
            color: #1e293b; 
            margin-bottom: 10px; 
            font-size: 20px;
        }}
        .test-meta {{ 
            color: #64748b; 
            margin-bottom: 15px; 
            font-size: 14px;
        }}
        .start-btn {{
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            padding: 12px 25px;
            text-decoration: none;
            border-radius: 8px;
            display: inline-block;
            font-weight: 600;
            transition: all 0.3s ease;
        }}
        .start-btn:hover {{
            transform: translateY(-2px);
            box-shadow: 0 8px 20px rgba(102, 126, 234, 0.4);
        }}
        .test-status {{
            padding: 8px 15px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            display: inline-block;
        }}
        .completed-status {{
            background: #dcfce7;
            color: #166534;
        }}
        .review-status {{
            background: #fef3c7;
            color: #92400e;
        }}
        .no-tests {{
            text-align: center;
            padding: 60px 20px;
            color: #64748b;
        }}
        .pending {{ border-left-color: #3b82f6; }}
        .submitted {{ border-left-color: #f59e0b; }}
        .completed {{ border-left-color: #10b981; }}
    </style>
</head>
<body>
    <div class="header">
        <div class="header-content">
            <h1>👋 Welcome, {user.get('display_name', user_id)}</h1>
            <a href="/logout" class="logout">Logout</a>
        </div>
    </div>
    
    <div class="container">
        <div class="stats">
            <div class="stat">
                <div class="stat-num">{len(my_tests)}</div>
                <div class="stat-label">Total Tests</div>
            </div>
            <div class="stat">
                <div class="stat-num">{len([t for t in my_tests if t['status'] == 'pending'])}</div>
                <div class="stat-label">Pending</div>
            </div>
            <div class="stat">
                <div class="stat-num">{len([t for t in my_tests if t['status'] == 'completed'])}</div>
                <div class="stat-label">Completed</div>
            </div>
            <div class="stat">
                <div class="stat-num">{user.get('exp', 0)}+</div>
                <div class="stat-label">Years Exp</div>
            </div>
        </div>
        
        <div class="section">
            <h2>📋 My Assessments</h2>
            {tests_html}
        </div>
    </div>
</body>
</html>'''

@app.route('/student/test/<test_id>', methods=['GET', 'POST'])
def student_test(test_id):
    if not session.get('user_id') or session.get('is_admin'):
        return redirect('/login')
    
    test = assignments.get(test_id)
    if not test or test['engineer_id'] != session['user_id']:
        return redirect('/student')
    
    if request.method == 'POST' and test['status'] == 'pending':
        answers = {}
        for i in range(18):  # 18 questions
            answer = request.form.get(f'answer_{i}', '').strip()
            if answer:
                answers[str(i)] = answer
        
        if len(answers) >= 15:  # At least 15 answers required
            test['answers'] = answers
            test['status'] = 'submitted'
            test['submitted_date'] = datetime.now().isoformat()
            
            # Auto-score the answers
            test['auto_scores'] = {}
            for i, answer in answers.items():
                if answer:
                    suggested_score, reasoning = analyze_answer_quality(
                        test['questions'][int(i)], answer, test['topic']
                    )
                    test['auto_scores'][i] = {
                        'score': suggested_score,
                        'reasoning': reasoning
                    }
        
        return redirect('/student')
    
    # If already submitted, show read-only view
    if test['status'] != 'pending':
        return redirect('/student')
    
    questions_html = ''
    for i, q in enumerate(test['questions']):
        questions_html += f'''
        <div class="question-card">
            <div class="question-header">
                <span class="question-number">Question {i+1} of 18</span>
                <span class="topic-badge">{test["topic"].upper()}</span>
            </div>
            <div class="question-text">{q}</div>
            <div class="answer-section">
                <label for="answer_{i}">Your Answer:</label>
                <textarea id="answer_{i}" name="answer_{i}" placeholder="Provide detailed technical answer..." required></textarea>
                <div class="char-count" id="count_{i}">0 characters</div>
            </div>
        </div>'''
    
    return f'''
<!DOCTYPE html>
<html>
<head>
    <title>{test["topic"].upper()} Assessment</title>
    <style>
        body {{ 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
            margin: 0; 
            min-height: 100vh;
        }}
        .header {{ 
            background: rgba(255,255,255,0.15); 
            backdrop-filter: blur(10px);
            color: white; 
            padding: 20px 0;
            position: sticky;
            top: 0;
            z-index: 100;
        }}
        .header-content {{
            max-width: 1000px;
            margin: 0 auto;
            padding: 0 20px;
            text-align: center;
        }}
        .container {{ 
            max-width: 1000px; 
            margin: 20px auto; 
            padding: 0 20px; 
        }}
        .test-info {{
            background: rgba(255,255,255,0.95);
            border-radius: 16px;
            padding: 25px;
            margin-bottom: 25px;
            text-align: center;
        }}
        .question-card {{
            background: rgba(255,255,255,0.95);
            border-radius: 16px;
            padding: 30px;
            margin: 25px 0;
            box-shadow: 0 8px 25px rgba(0,0,0,0.1);
        }}
        .question-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }}
        .question-number {{
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            padding: 8px 16px;
            border-radius: 20px;
            font-weight: 600;
            font-size: 14px;
        }}
        .topic-badge {{
            background: #f1f5f9;
            color: #64748b;
            padding: 6px 12px;
            border-radius: 15px;
            font-size: 12px;
            font-weight: 600;
        }}
        .question-text {{
            background: linear-gradient(135deg, #f8fafc, #f1f5f9);
            padding: 20px;
            border-radius: 12px;
            margin-bottom: 20px;
            border-left: 4px solid #667eea;
            line-height: 1.6;
            color: #1e293b;
        }}
        .answer-section label {{
            display: block;
            margin-bottom: 8px;
            font-weight: 600;
            color: #374151;
        }}
        textarea {{
            width: 100%;
            min-height: 120px;
            padding: 16px;
            border: 2px solid #e5e7eb;
            border-radius: 12px;
            font-size: 14px;
            font-family: inherit;
            resize: vertical;
            transition: border-color 0.3s ease;
        }}
        textarea:focus {{
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }}
        .char-count {{
            text-align: right;
            font-size: 12px;
            color: #64748b;
            margin-top: 5px;
        }}
        .submit-section {{
            background: rgba(255,255,255,0.95);
            border-radius: 16px;
            padding: 30px;
            text-align: center;
            margin-top: 30px;
        }}
        .warning {{
            background: #fef3c7;
            border: 1px solid #f59e0b;
            padding: 16px;
            border-radius: 12px;
            margin-bottom: 20px;
            color: #92400e;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        .btn {{
            padding: 14px 28px;
            border: none;
            border-radius: 10px;
            font-weight: 600;
            cursor: pointer;
            margin: 8px;
            text-decoration: none;
            display: inline-block;
            transition: all 0.3s ease;
        }}
        .btn-primary {{
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
        }}
        .btn-primary:hover {{
            transform: translateY(-2px);
            box-shadow: 0 8px 20px rgba(102, 126, 234, 0.4);
        }}
        .btn-secondary {{
            background: rgba(107,114,128,0.1);
            color: #374151;
        }}
        .progress-bar {{
            background: #e5e7eb;
            height: 6px;
            border-radius: 3px;
            margin: 20px 0;
            overflow: hidden;
        }}
        .progress-fill {{
            background: linear-gradient(135deg, #667eea, #764ba2);
            height: 100%;
            width: 0%;
            transition: width 0.3s ease;
        }}
    </style>
</head>
<body>
    <div class="header">
        <div class="header-content">
            <h1>📝 {test["topic"].upper()} Assessment</h1>
            <p>Physical Design Technical Evaluation</p>
        </div>
    </div>
    
    <div class="container">
        <div class="test-info">
            <h2>📋 Assessment Details</h2>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-top: 20px;">
                <div><strong>Questions:</strong> 18 Technical</div>
                <div><strong>Max Points:</strong> 180 (10 each)</div>
                <div><strong>Due Date:</strong> {test["due"][:10]}</div>
                <div><strong>Topic:</strong> {test["topic"].upper()}</div>
            </div>
            <div class="progress-bar">
                <div class="progress-fill" id="progressBar"></div>
            </div>
            <div id="progressText">Progress: 0/18 questions answered</div>
        </div>
        
        <form method="POST" id="assessmentForm">
            {questions_html}
            
            <div class="submit-section">
                <div class="warning">
                    ⚠️ <strong>Important:</strong> Review all answers before submitting. You cannot edit after submission.
                </div>
                <button type="submit" class="btn btn-primary" id="submitBtn" disabled>Submit Assessment</button>
                <a href="/student" class="btn btn-secondary">Save & Exit</a>
            </div>
        </form>
    </div>
    
    <script>
        // Character counting and progress tracking
        const textareas = document.querySelectorAll('textarea');
        const progressBar = document.getElementById('progressBar');
        const progressText = document.getElementById('progressText');
        const submitBtn = document.getElementById('submitBtn');
        
        textareas.forEach((textarea, index) => {{
            const counter = document.getElementById(`count_${{index}}`);
            
            textarea.addEventListener('input', function() {{
                const length = this.value.length;
                counter.textContent = `${{length}} characters`;
                
                // Update progress
                updateProgress();
            }});
        }});
        
        function updateProgress() {{
            const answered = Array.from(textareas).filter(ta => ta.value.trim().length >= 20).length;
            const percentage = (answered / 18) * 100;
            
            progressBar.style.width = percentage + '%';
            progressText.textContent = `Progress: ${{answered}}/18 questions answered`;
            
            // Enable submit button if at least 15 questions answered
            submitBtn.disabled = answered < 15;
            if (answered >= 15) {{
                submitBtn.style.opacity = '1';
                submitBtn.style.cursor = 'pointer';
            }} else {{
                submitBtn.style.opacity = '0.6';
                submitBtn.style.cursor = 'not-allowed';
            }}
        }}
        
        // Form submission validation
        document.getElementById('assessmentForm').addEventListener('submit', function(e) {{
            const answered = Array.from(textareas).filter(ta => ta.value.trim().length >= 20).length;
            if (answered < 15) {{
                e.preventDefault();
                alert('Please answer at least 15 questions (minimum 20 characters each) before submitting.');
                return false;
            }}
            
            if (!confirm('Are you sure you want to submit? You cannot edit answers after submission.')) {{
                e.preventDefault();
                return false;
            }}
        }});
        
        // Auto-save to localStorage
        textareas.forEach((textarea, index) => {{
            const key = `test_{test["id"]}_answer_${{index}}`;
            textarea.value = localStorage.getItem(key) || '';
            
            textarea.addEventListener('input', function() {{
                localStorage.setItem(key, this.value);
            }});
        }});
        
        // Initial progress update
        updateProgress();
    </script>
</body>
</html>'''

if __name__ == '__main__':
    try:
        print("🚂 Starting Railway Flask App...")
        init_data()
        print("✅ Data initialized successfully")
        
        port = int(os.environ.get('PORT', 5000))
        print(f"✅ Starting server on port {port}")
        
        app.run(host='0.0.0.0', port=port, debug=False)
        
    except Exception as e:
        print(f"❌ STARTUP ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        exit(1)
