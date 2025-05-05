let mediaRecorder;
let audioChunks = [];

document.getElementById('recordButton').addEventListener('click', async () => {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder = new MediaRecorder(stream);
    
    mediaRecorder.ondataavailable = event => {
        audioChunks.push(event.data);
    };

    mediaRecorder.onstop = () => {
        const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
        const audioUrl = URL.createObjectURL(audioBlob);
        const audio = document.createElement('audio');
        audio.src = audioUrl;
        audio.controls = true;
        document.getElementById('recordingsList').appendChild(audio);

        // Upload the audio file
        const formData = new FormData();
        formData.append('audio', audioBlob, 'recording.wav');
       /*
        fetch('/upload', {
            method: 'POST',
            body: formData
        });
        */
        $.ajax({
            type: "POST",
            url: "/upload", // Your server endpoint
            data: formData,
            processData: false, // Prevent jQuery from processing the data
            contentType: false, // Let the server handle content type
            success: function (response) {
                file_uploaded = true;
                console.log("File uploaded successfully!", response);
                process_message(false, response, audio); // no_files = false
            },
            error: function (error) {
                console.error("Error uploading file:", error);
            }
        });

    };

    mediaRecorder.start();
    document.getElementById('recordButton').style = "cursor: pointer;display:none";
    document.getElementById('stopButton').style = "cursor: pointer;display:inline";
});

document.getElementById('stopButton').addEventListener('click', () => {
    mediaRecorder.stop();
    document.getElementById('recordButton').style = "cursor: pointer;display:inline";
    document.getElementById('stopButton').style = "cursor: pointer;display:none";
});
