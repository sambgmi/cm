from flask import Flask, render_template

app = Flask(__name__)

# Dummy photographers data
photographers = [
    {
        'id': 'p1',
        'name': 'Alex Johnson',
        'specialty': 'Wedding Photography',
        'bio': 'Capturing timeless wedding memories.',
        'image': 'https://picsum.photos/id/1005/400/300',
        'availability': ['2025-06-21', '2025-06-25', '2025-06-30']
    },
    {
        'id': 'p2',
        'name': 'Sarah Miller',
        'specialty': 'Portrait Photography',
        'bio': 'Telling stories through expressive portraits.',
        'image': 'https://picsum.photos/id/1011/400/300',
        'availability': ['2025-07-01', '2025-07-02', '2025-07-03']
    },
    {
        'id': 'p3',
        'name': 'Michael Chen',
        'specialty': 'Event Photography',
        'bio': 'Bringing life to your events with photos.',
        'image': 'https://picsum.photos/id/1012/400/300',
        'availability': ['2025-06-24', '2025-06-28', '2025-06-29']
    }
]


# Landing page
@app.route('/')
def index():
    return render_template('index.html')

# Photographers page
@app.route('/photographers')
def show_photographers():
    return render_template('photographers.html', photographers=photographers)

@app.route('/book/<photographer_id>')
def book_photographer(photographer_id):
    selected = next((p for p in photographers if p['id'] == photographer_id), None)
    if not selected:
        return "Not found", 404
    return render_template('book.html', photographer=selected)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
