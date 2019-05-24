$("#submitButton").on("click", function() {
    onClickSubmitButton();
});
function onClickSubmitButton() {
    let urlGet = "http://c6043f4f.ngrok.io/getDiff";
    let commitUser = $("#commitUser").val();
    let commitTarget = $("#commitTarget").val();

    if (commitUser != "" && commitTarget != "") {
        $.get(urlGet + "?commitUser=" + commitUser + "&commitTarget=" + commitTarget, function(data, status) {
            if (data.hasOwnProperty('message')) {
                alert(data.message);
            } else {
                displayResult(data);
            }
        });
    } else {
        alert('Please insert non-empty commit ids')
    }

}

function displayResult(data) {
    $("#diffContainer").empty();
    let parsed = htmlEntities(data.diff);
    let elmt = "<div><pre><code>" + parsed +"</code></pre></div>";
    $("#diffContainer").append(elmt);
}

function htmlEntities(str) {
    return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}