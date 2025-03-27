import os
from flask import Flask, render_template, request, flash, redirect, url_for, jsonify
from werkzeug.utils import secure_filename
import pandas as pd
import plotly.express as px
import plotly.utils
import json
from models import db, DataRecord, initialize_db
from peewee import fn, SQL

app = Flask(__name__)

# Initialize the database
initialize_db()
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-here')  # Change this to a secure key in production
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
ALLOWED_EXTENSIONS = {'csv'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part', 'error')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('No selected file', 'error')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            try:
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                
                # Read CSV and insert into database
                df = pd.read_csv(filepath)
                
                # Insert data into database
                with db.atomic():
                    for _, row in df.iterrows():
                        DataRecord.create(
                            name=str(row.get('name', 'Unknown')),
                            category=str(row.get('category', 'Other')),
                            value=float(row.get('value', 0.0))
                        )
                
                flash('File successfully uploaded and data processed. You can now visualize the data.', 'success')
                return redirect(url_for('visualize'))
            except Exception as e:
                flash(f'Error processing file: {str(e)}', 'error')
                return redirect(request.url)
    
    return render_template('upload.html')

@app.route('/fish', methods=['GET'])
def fish():
    search_query = request.args.get('search', '')
    if search_query:
        fish_data = DataRecord.select().where(DataRecord.name.contains(search_query))
    else:
        fish_data = DataRecord.select()
    
    return render_template('fish.html', fish_data=fish_data)

@app.route('/visualize')
def visualize():
    try:
                # print("Entering visualize route")  # Debug log

        # Use database context manager for all database operations
        with db:
            # Check if we have any data
            count = DataRecord.select().count()
                # print(f"Found {count} records")  # Debug log

            if count == 0:
                # print("No records found, redirecting to upload")  # Debug log
                flash('No data available. Please upload a CSV file first.', 'warning')
                return redirect(url_for('upload'))

                # print("Querying category counts")  # Debug log

            # Query 1: Bar chart of counts by category
            category_counts = list(DataRecord
                                 .select(DataRecord.category, SQL('COUNT(*)').alias('count'))
                                 .group_by(DataRecord.category)
                                 .dicts())
                # print(f"Category counts: {category_counts}")  # Debug log


                # print("Querying values")  # Debug log

            # Query 2: Histogram of values
            min_value = float(request.args.get('min_value', 0))
            values = list(DataRecord
                         .select(DataRecord.value)
                         .where(DataRecord.value >= min_value)
                         .dicts())
            print(f"Found {len(values)} values")  # Debug log

        # Create visualizations (outside db context since we have the data)
        df_categories = pd.DataFrame(category_counts)
        fig1 = {
            'data': [{
                'x': df_categories['category'].tolist(),
                'y': df_categories['count'].tolist(),
                'type': 'bar',
                'marker': {'color': '#0d6efd'},
                'name': 'Species Count'
            }],
            'layout': {
                'title': 'Fish Species by Habitat',
                'showlegend': False,
                'plot_bgcolor': 'white',
                'paper_bgcolor': 'white',
                'xaxis': {'title': 'Habitat Type'},
                'yaxis': {'title': 'Number of Species'}
            }
        }
        chart1_json = json.dumps(fig1)

        df_values = pd.DataFrame(values)
        fig2 = {
            'data': [{
                'x': df_values['value'].tolist(),
                'type': 'histogram',
                'marker': {'color': '#198754'},
                'name': 'Size Distribution'
            }],
            'layout': {
                'title': 'Fish Size Distribution',
                'showlegend': False,
                'plot_bgcolor': 'white',
                'paper_bgcolor': 'white',
                'xaxis': {'title': 'Size (cm)'},
                'yaxis': {'title': 'Number of Species'}
            }
        }
        chart2_json = json.dumps(fig2)
        
        return render_template('visualization.html',
                             chart1_json=chart1_json,
                             chart2_json=chart2_json,
                             min_value=min_value)
    
    except Exception as e:
        # print(f"Error in visualize route: {str(e)}")  # Debug log
        flash(f'Error generating visualizations: {str(e)}', 'error')
        return redirect(url_for('home'))

@app.route('/api/stats')
def get_stats():
    try:
        # Calculate statistics from the database
        total_records = DataRecord.select().count()
        
        # Get average value
        avg_value = (DataRecord
                    .select(SQL('AVG(value)').alias('avg_value'))
                    .scalar() or 0.0)
        
        # Get maximum value
        max_value = (DataRecord
                    .select(SQL('MAX(value)').alias('max_value'))
                    .scalar() or 0.0)
        
        # Get unique category count
        category_count = (DataRecord
                         .select(DataRecord.category)
                         .distinct()
                         .count())
        
        return jsonify({
            'total_records': total_records,
            'average_value': float(avg_value),
            'max_value': float(max_value),
            'category_count': category_count
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Database initialization
@app.before_request
def before_request():
    if db.is_closed():
        db.connect()

@app.after_request
def after_request(response):
    if not db.is_closed():
        db.close()
    return response

def initialize():
    # Ensure upload directory exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Initialize database and create tables if they don't exist
    db.connect()
    db.create_tables([DataRecord], safe=True)
    db.close()

# Run the application
if __name__ == '__main__':
    initialize()
    app.run(debug=True, port=5000)
