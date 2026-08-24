async function handleFormSubmission(event) {
    event.preventDefault(); // Stop the default form submission

    const form = event.target;
    const data = {
        exercise_ID: form.exercise_ID.value,
        participant_ID: form.participant_ID.value,
        comment: form.comment.value,
    };

    const fileInput = form.picture;
    data.files = []
    if (fileInput.files.length > 0) {
        for (let i = 0; i < fileInput.files.length; i++) {
            if(fileInput.files[i].size > 5000000) {
                alert("File " + fileInput.files[i].name + " is too big! 5mb max please");
                break;
            }
            data.files.push({
                bytes: await fileToBase64(fileInput.files[i]),
                index: i,
                filename: fileInput.files[i].name,
                extension:fileInput.files[i].name.split('.').pop(),
                mediaType: fileInput.files[i].type
            });
        }
    }
    form.innerHTML = '<p>Sending...<p>';
    try {
        const response = await fetch('/api/odata/v4/participant/submission', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        });
        const res = await response.json()
        console.log(res.value);
        if (res.value == "All good") {
            const formCallout = document.getElementById("submit-form").parentNode;
            formCallout.replaceWith(createElementFromHTML(successString));
        }
    } catch (err) {
        console.error('Error:', err);
        const formCallout = document.getElementById("submit-form").parentNode;
        formCallout.replaceWith(createElementFromHTML(errorString));
    }
};

function fileToBase64(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result);
        reader.onerror = reject;
        reader.readAsDataURL(file);
    });
}

function createElementFromHTML(htmlString) {
    var div = document.createElement('div');
    div.innerHTML = htmlString.trim();

    return div.firstChild;
}

const successString = `<div class="alert callout note">
            <p class="title"><span class="icon fa-solid fa-check"></span>Exercise submitted!</p>
            <p>We have received your results, we will review it and let you know.</p>
            </div>`;

const errorString = `<div class="alert callout warning">
            <p class="title"><span class="icon fa-solid fa-check"></span>There was a problem submitting the result!</p>
            </div>`;