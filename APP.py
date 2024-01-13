from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename
import os

import jpype
import mpxj
import json

app = Flask(__name__)
CORS(app)

shutdown_requested = False

@app.route('/')
def home():
    return jsonify(message='Welcome')

@app.route('/readxerfile', methods=['POST'])
def upload_file():
    global shutdown_requested
    try:
        if 'file' not in request.files:
            return 'No file part'
        
        file = request.files['file']
        
        # Check if the file has a .xer extension
        if not file.filename.endswith('.xer'):
            return jsonify({"message":'Invalid file format. Please upload a .xer file.'})

        filename = secure_filename(file.filename)
        file.save(os.path.join('uploadfiles/', filename))

        FILE_NAME = 'uploadfiles/' + filename

        # Start the JVM
        if not jpype.isJVMStarted():
            jpype.startJVM(jpype.getDefaultJVMPath())

        # Import the required Java classes
        ProjectReader = jpype.JClass('net.sf.mpxj.reader.UniversalProjectReader')
        File = jpype.JClass('java.io.File')

        # Create a reader instance
        reader = ProjectReader()

        project = reader.read(File(FILE_NAME))

        # Get the tasks
        tasks = project.getTasks()

        OUTPUT_DIRECTORY = "output/" + FILE_NAME.split('.xer')[0].split('/')[1] + '.json'

        # final Output
        final = {}

        # Create a dictionary to hold the task data
        data = []
        links = []


        # Loop through each task
        for task in tasks:
            attributes = {
                'id': str(task.getID()),
                "Activity ID": str(task.getActivityID()),
                "$custom_data": {
                    "critical": str(task.getCritical()),
                    "type": str(task.getType()),
                    'uid': str(task.getUniqueID()),
                },
                "$raw": {
                    "actualDuration": str(task.getActualDuration()),
                    "actualFinish": str(task.getActualFinish()),
                    "actualStart": str(task.getActualStart()),
                    'duration': str(task.getDuration()),
                    'finish': str(task.getFinish()),
                    'start': str(task.getStart()),
                    'work': str(task.getCost())
                },
                'duration': str(task.getDuration()),
                "open": str(task.getActive()),
                "parent": str(task.getParentTask().getUniqueID()) if task.getParentTask() is not None else None,
                'progress': str(task.getPercentageComplete()),
                'resources': str(task.getResourceNames()),
                'start_date': str(task.getStart()),
                'text': str(task.getName()),

            }

            # Get the predecessors
            predecessors = task.getPredecessors()

            if predecessors:
                pred_list = []
                c = 0
                for pred in predecessors:
                    pred_dict = {
                        'id': c,
                        '$lag_unit': "h",
                        'lag': str(pred.getLag()),
                        'source': str(pred.getSourceTask().getUniqueID()),
                        'target': str(pred.getTargetTask().getUniqueID()),
                        'type': str(pred.getType()),
                    }
                    pred_list.append(pred_dict)
                    c += 1
                links.extend(pred_list)

            # Add the task to the dictionary
            data.append(attributes)

        final['data'] = data
        final['links'] = links

        # Convert the task dictionary to a JSON string
        task_json = json.dumps(final, indent=5)

        # Shutdown the JVM
        shutdown_requested = True

        return task_json
    except Exception as e:
        return jsonify(error=str(e))

if __name__ == '__main__':
    app.run()
    if shutdown_requested:
        jpype.shutdownJVM()
