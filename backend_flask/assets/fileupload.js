// Assuming you have an input element with ID "fileInput" and a form with ID "uploadForm"
const fileInput = document.getElementById("fileInput");
//const uploadForm = document.getElementById("uploadForm");
const fileInputPreview = document.getElementById("preview2");
file_uploaded = false;
//console.log(uploadForm);
document.addEventListener("paste", (event) => {
    const clipboardData = event.clipboardData || window.clipboardData;
    const items = clipboardData.items;

    for (const item of items) {
        if (item.kind === "file") {
            console.log(item)
            const file = item.getAsFile();
            // You can handle the file here (e.g., display its name, validate, etc.)
            // Then set the value of the file input:
            // fileInput.files = [file];

            // Assuming you have an input element with ID "fileInput" and an array of files called "myFiles"
            //const fileInput = document.getElementById("fileInput");
            const myFiles = [file];

            // Create a new DataTransfer object
            const dataTransfer = new DataTransfer();

            // Add each file from your array to the DataTransfer object
            for (const file of myFiles) {
                dataTransfer.items.add(file);
            }

            // Get the new FileList from the DataTransfer object
            const myFileList = dataTransfer.files;

            // Set it as the files property of the DOM node (your file input)
            fileInput.files = myFileList;


            break; // Assuming you want to handle only the first file
        }
    }
});

/*
// Optional: Submit the form when the file input changes
fileInput.addEventListener("change", () => {
    console.log("Uploading file");
    uploadForm.submit();
});

*/
function uploadFile(_file_element_id) {
    //const fileInput = document.getElementById("fileInput");
    const fileInput = document.getElementById(_file_element_id);
    
    const file = fileInput.files[0]; // Get the selected file

    const formData = new FormData();
    formData.append("myFile", file); // Append the file to FormData
    preview_img = document.getElementById('preview2');
    if(preview_img != null)
    {
        preview_img.style = "display:none";
    }
    $.ajax({
        type: "POST",
        url: "/upload", // Your server endpoint
        data: formData,
        processData: false, // Prevent jQuery from processing the data
        contentType: false, // Let the server handle content type
        success: function (response) {
            file_uploaded = true;
            console.log("File uploaded successfully!", response);
            file_in_id = "#" + _file_element_id;
            //$("#fileInput").val('');
            $(file_in_id).val('');

            process_message(false, response); // no_files = false
        },
        error: function (error) {
            console.error("Error uploading file:", error);
        }
    });
}

var loadFile = function (event) {
    var reader = new FileReader();
    reader.onload = function () {
        var output = document.getElementById('output');
        if (output != null)
            output.src = reader.result;

        var text_box = document.getElementById('problem_text');
        text_box.style = "display:none";
        output.style = "display: inline";

    };
   // console.log(event);
    reader.readAsDataURL(event.target.files[0]);
};

var loadFile2 = function (event) {
    var reader = new FileReader();
    reader.onload = function () {
        console.log("init preview");
        var output = document.getElementById('preview2');
        if (output != null)
            output.src = reader.result;
        output.style = "display: inline";

    };
    console.log(event);
    reader.readAsDataURL(event.target.files[0]);
};


fileInputPreview.addEventListener("click", () => {
    console.log("handling click event");
    $("fileInput").val('');
    fileInputPreview.style= "display:none";

});