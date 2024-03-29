let ws;
let xhr;
let sender_id = Date.now();
sender_id = sender_id.toString().slice(-5)
document.querySelector("#sender-id").textContent = sender_id;

function CreateWebsocket(){
    let receiver_id = document.getElementById("receiver-id").value;
    if(receiver_id == sender_id){
        alert("You know you are going to be sending to yourself right?");
    }
    let currentUrl = window.location.hostname;

    ws = new WebSocket(`ws://${currentUrl}/ws/${sender_id}/${receiver_id}`);
    console.log("This is ws: ", ws)

    ws.onmessage = function(event) {
        const message = event.data
        try{
            const jsonMessage = JSON.parse(message);
            // # , '.mkv', '.avi', '.mov', '.wmv', '.flv']
            allowedVideoExtensions = '.mp4';
            jsonMessage.forEach(function(item) {
                if (item.includes(allowedVideoExtensions)){
                    createReceivedFileElement(item, true);
                }else{
                    createReceivedFileElement(item, false);
                } 
            });
            }catch(e){
                alert(e);
        }
        }
    };


function uploadFile() {
    const formData = new FormData(document.getElementById('upload-form'));
    const fileInput = document.getElementById('file');
    const files = fileInput.files;

    const fileNames = Array.from(files).map(file => file.name);
    console.log("files sender is sending", fileNames);
    
    if (!ws){
        alert("Connect to someone first");
        return;
    }
    if (files.length === 0){
        alert("Please select a file.");
        return;
    }

    xhr = new XMLHttpRequest();
    xhr.open('POST', '/upload-files', true);

    xhr.upload.onprogress = function (event) {
        
        if (event.lengthComputable) {
            const progressBar = document.getElementById('upload-progress');
            const progressNumber = document.getElementById('progress_number');

            const percentComplete = (event.loaded / event.total) * 100;
            progressBar.style.width = percentComplete + '%';
            progressNumber.innerHTML = percentComplete.toFixed(2) + '%';
        }
    };

    xhr.onload = function () {
        if (xhr.status === 200) {
            alert('Upload successful!');
            resetProgressBarAndPercent();
            console.log("filenames are", fileNames);
            ws.send(JSON.stringify(fileNames));
        } else {
            alert('Upload failed. Status: ' + xhr.status);
        }
    };

    xhr.onerror = function() {
        alert('Error occurred while uploading the file.');
    };

    xhr.send(formData);
}

function resetProgressBarAndPercent(){
    document.getElementById('upload-progress').style.width = "0%";
    document.getElementById('progress_number').innerHTML = "0%";
}

function cancelUpload() {
    if (xhr) {
        xhr.abort();
        alert('Upload canceled.');
        resetProgressBarAndPercent();
    } else {
        alert('No upload in progress.');
    }
}

let streamTab;
function createReceivedFileElement(fileName, streamable) {
    const receivedFileElement = document.createElement('div');
    receivedFileElement.classList.add('received-file');

    const fileNameSpan = document.createElement('span');
    fileNameSpan.textContent = fileName;
    receivedFileElement.appendChild(fileNameSpan);

    const downloadButton = document.createElement('button');
    downloadButton.textContent = 'Download';
    downloadButton.href = `download/${fileName}`;
    downloadButton.onclick = function() {
        window.location.href = downloadButton.href;
    };
    receivedFileElement.appendChild(downloadButton);

    const videoElement = document.getElementById("videoPlayer");
    if (streamable){
        const streamButton = document.createElement('button');
        streamButton.textContent = 'Stream';
        streamButton.href = `stream/${fileName}`;
        streamButton.onclick = function() {
            const source = document.createElement("source");
            source.src = `stream/${fileName}`;
            source.type = "video/mp4";
            videoElement.appendChild(source);
            videoElement.load();
            // streamTab = window.open(streamButton.href);
        };
        receivedFileElement.appendChild(streamButton);
    }
    // Create delete button
    const deleteButton = document.createElement('button');
    deleteButton.textContent = 'Delete';
    deleteButton.addEventListener('click', function() {
        videoElement.src = "";
        videoElement.load();

        // Make a DELETE request to the delete endpoint
        fetch(`/delete-file/${fileName}`, {
            method: 'DELETE',
        })
        .then(response => {
            if (response.ok) {
                console.log('File deleted successfully');
                receivedFileElement.remove(); // Remove the file element from the DOM
            } else {
                throw new Error('Failed to delete file');
            }
        })
        .catch(error => {
            console.error('Error:', error);
        });
    });
    receivedFileElement.appendChild(deleteButton);

    // Append the created element to the received files list
    const receivedFilesList = document.getElementById('received-files');
    receivedFilesList.appendChild(receivedFileElement);
}

window.onbeforeunload = function() {
    if (streamTab && !streamTab.closed) {
        return "You have an active stream tab. Closing this tab will also close the stream tab.";
    }
};