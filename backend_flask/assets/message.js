// Initialize an array to store the conversation history
let conversationHistory = [];
let conversationHistory_key = user_conversationHistory_key; //'{ROLE}-{OBJECTIVE}'
let ai_model_name = user_ai_model_name; //"{AI_MODEL}";

function reset_selections() {
    // hide the image
    var output = document.getElementById('output');
    if (output != null)
        output.style = "width: 400px; height: 300px; display:none";

    $('file-upload').val('');
    // display the text box
    var text_box = document.getElementById('problem_text');
    if (text_box != null) {
        text_box.value = '';
        text_box.style = "width: 400px; height: 300px; display: inline";
    }
}


// Function to load the conversation history from localStorage
function loadConversationHistory() {
    const storedHistory = localStorage.getItem(conversationHistory_key);
    console.log(storedHistory);
    if (storedHistory != null) {
        conversationHistory = JSON.parse(storedHistory);
        conversationHistory.forEach(message => {
            addMessage(message.content, message.role === "user" ? "user" : "bot");
        });
    } else {
        // Display the welcome message if there's no stored history
        displayWelcomeMessage();
    }
}

function clearHistory() {
    $("#fileInput").val('');
    // Clear the chat container
    const chatContainer = document.getElementById("chat-container");
    chatContainer.innerHTML = '';

    // Clear the conversation history array
    conversationHistory = [];

    // Clear the conversation history from localStorage
    localStorage.removeItem(conversationHistory_key);

    // Display the welcome message again
    displayWelcomeMessage();
}



// Function to save the conversation history to localStorage
function saveConversationHistory() {
    localStorage.setItem(conversationHistory_key, JSON.stringify(conversationHistory));
}

// Function to add a message to the chat container
function addMessage(message, sender) {
    const chatContainer = document.getElementById("chat-container");
    const messageElement = document.createElement("div");
    messageElement.className = `message ${sender}-message`;

    const messageText = document.createElement("div");
    messageText.className = "message-text";
    messageText.innerHTML = message.replace(/\n/g, "<br>");

    messageElement.appendChild(messageText);
    chatContainer.appendChild(messageElement);

    // Scroll to the bottom of the chat container
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

// Function to display the welcome message from the bot
function displayWelcomeMessage() {
    const welcomeMessage = "Hello! I am Aanya, your tutor . How should I help you?" ; //"Hello! I'm Ekam Tutor. How can I help you today?";
    addMessage(welcomeMessage, "bot");
}

// Function to display a temporary "Generating response..." message from the bot
function displayGeneratingMessage() {
    const generatingMessage = "Generating response...";
    addMessage(generatingMessage, "bot");
    return generatingMessage;
}

// Function to remove the "Generating response..." message from the chat container
function removeGeneratingMessage(generatingMessage) {
    const chatContainer = document.getElementById("chat-container");
    chatContainer.removeChild(chatContainer.lastChild);
}

function get_ai_model() {

    ai_model_name = "";
    if (radio1.checked)
        ai_model_name = $("#radio1").checkboxradio("option", "label");
    if (radio2.checked)
        ai_model_name = $("#radio2").checkboxradio("option", "label");
    if (radio3.checked)
        ai_model_name = $("#radio3").checkboxradio("option", "label");

    return ai_model_name;
}

function process_message(no_file, filePath, audio = null) {
    input = document.getElementById("message");
    message = input.value.trim();

    ai_model_name = get_ai_model();
    console.log(ai_model_name);


    grade_level_id = document.getElementById("grade_level");
    problem_text_id = document.getElementById("problem_text");
    subject_name_id = document.getElementById("subject_name");
    file_upload_id = document.getElementById("file-upload");

    if (grade_level_id == null) {
        grade_level = "";
    }
    else {
        grade_level = grade_level_id.value;
    }
    if (problem_text_id == null) {
        problem_text = "";
    }
    else {
        problem_text = problem_text_id.value;
    }

    if (subject_name_id == null) {
        subject_name = "";
    }
    else {
        subject_name = subject_name_id.value;
    }

    //dd_selected = document.getElementById("speed");
    //ai_model_name = dd_selected.value;
    //console.log(ai_model_name);
    first_time = (conversationHistory.length === 0)
    msg_required = false;
    if (file_upload_id != null) {
        if (problem_text.length === 0 && file_upload_id.files.length == 0) {
            msg_required = true;
        }

    }
    // Do not proceed if the message is empty
    if (message.length === 0 && no_file) {
        if (msg_required) {
            alert('Please enter a message')
            return;
        }
        else {
            message = user_custom_message;
            message = message.replace('{grade_level}', grade_level);
            message = message.replace('{subject_name}', subject_name);
            message = message.replace('{problem_text}', problem_text);
        }
    }

    if (message.length === 0 && !no_file) {
        if (first_time) {
            /*
            if (user_objective == "helponproblem")
                message = "Help me in " + subject_name + " with step by step guidance for this problem " + problem_text + "<br/>"; // this will be replaced by image
            //message += "<img src='/"+filePath+"' style='height:50px;width:50px' />";        
            if (user_objective == "teachme")
                message = "I am in " + grade_level + "and want to learn about" + problem_text + "<br/>";
            if (user_objective == "worksheets")
                message = ("Generate worksheet for {grade_level} on {problem_text}").replace("{grade_level}",grade_level).replace("{problem_text}",problem_text);// + grade_level + " want to learn about" + problem_text + "<br/>";
    
            */
            message = user_custom_message;
            message = message.replace('{grade_level}', grade_level);
            message = message.replace('{subject_name}', subject_name);
            message = message.replace('{problem_text}', problem_text);
            if (message.length === 0)
                message += "<br/>";

        }
        if (audio != null) {
            console.log(audio);
            str = document.getElementById("recordingsList").innerHTML;
            console.log(str);
            message += str;
        }
        else {
            message += "<img src='/" + filePath.replace('\\', '/') + "' class='imgpreview_inline'  />";

        }
    }


    // Display the user's message and update the conversation history
    addMessage(message, "user");
    conversationHistory.push({ role: "user", content: message });
    saveConversationHistory(); // Save the updated conversation history to localStorage

    input.value = "";
    input.focus();
    if (problem_text_id != null)
        problem_text_id.value = "";

    // Display the "Generating response..." message
    const generatingMessage = displayGeneratingMessage();
    role2 = user_role; //'{ROLE}';
    objective2 = user_objective; //"{OBJECTIVE}";
    // Send a request to the server to generate a response
    fetch("/generate", {
        method: "POST",
        body: JSON.stringify({
            message: message, history: conversationHistory,
            role: role2, objective: objective2,
            ai_model: ai_model_name,
            filePath: filePath
        }),
        headers: {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    })
        .then(response => response.json())
        .then(data => {
            // Remove the "Generating response..." message and display the bot's response
            removeGeneratingMessage(generatingMessage);
            addMessage(data, "bot");
            conversationHistory.push({ role: "assistant", content: data });
            saveConversationHistory(); // Save the updated conversation history to localStorage
        });

}

function process_input(file_control_name, first_prompt = false) {
    no_file = true;
    var fileInput = document.getElementById(file_control_name);
    if (fileInput != null) {
        if ('files' in fileInput) {
            if (fileInput.files.length === 0) {
                console.log("No files selected.");
            } else {
                no_file = false;
                console.log('Uploading file');
                uploadFile(file_control_name);
            }
        }
    }



    if (no_file) {
        process_message(no_file, "");
    }
}

// Event listener for the form submission
document.getElementById("chat-form").addEventListener("submit", function (event) {
    event.preventDefault();

    process_input("fileInput", false);


});

// Event listener for the "Clear History" button
document.getElementById("clear-history").addEventListener("click", function () {
    console.log("clearing history");
    //clearHistory();
    reset_selections();
    ele = document.getElementById("objective_selections");
    if (ele != null)
        $("#objective_selections").dialog("open");
    else
        clearHistory();
});



// Load the conversation history when the page loads
loadConversationHistory();

const textarea = document.getElementById("message");
//var is_posted_from_message_box = false;
textarea.addEventListener("keydown", function (event) {
    if (event.key === "Enter" && !event.shiftKey && !event.altKey) {
        event.preventDefault();
        //document.forms[0].submit();
        process_input("fileInput", false);
    }
    if (event.key === "Enter" && !event.shiftKey && event.altKey)
        textarea.value += "\n";

});
