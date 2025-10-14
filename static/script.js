// Modal functionality
const modal = document.getElementById("signupModal");
document.getElementById("tryFreeBtn").onclick = () => modal.style.display="block";
document.querySelector(".close").onclick = () => modal.style.display="none";
window.onclick = e => { if(e.target == modal) modal.style.display="none"; }

// API key request
document.getElementById("submitKey").onclick = async () => {
    const email = document.getElementById("email").value;
    if(!email) {
        alert("Please enter your email");
        return;
    }

    try {
        const res = await fetch("/generate-free-key", {
            method:"POST",
            headers: {"Content-Type":"application/json"},
            body: JSON.stringify({email})
        });
        const data = await res.json();

        if(data.api_key) {
            document.getElementById("message").innerText = "✅ Your Free API Key: " + data.api_key + "\nLimit: " + data.free_limit;
        } else {
            document.getElementById("message").innerText = "❌ " + (data.error || "Error generating key");
        }
    } catch(err) {
        document.getElementById("message").innerText = "❌ Network or server error";
    }
};
