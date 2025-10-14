function refreshCaptcha(e){e.preventDefault();document.getElementById("captcha-image").src="/captcha?"+new Date().getTime();}
const modal=document.getElementById("signupModal"),tryBtn=document.getElementById("tryFreeBtn"),closeSpan=document.getElementsByClassName("close")[0],getKeyBtn=document.getElementById("getKeyBtn"),emailInput=document.getElementById("emailInput"),apiKeyDisplay=document.getElementById("apiKeyDisplay"),copyKeyBtn=document.getElementById("copyKeyBtn");
tryBtn.onclick=()=>modal.style.display="block";
closeSpan.onclick=()=>modal.style.display="none";
window.onclick=e=>{if(e.target==modal)modal.style.display="none";}
getKeyBtn.onclick=async ()=>{
    const email=emailInput.value.trim();
    if(!email){apiKeyDisplay.className="error";apiKeyDisplay.textContent="❌ Enter your email";copyKeyBtn.style.display="none";return;}
    try{
        const res=await fetch("/generate-free-key",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({email})});
        const data=await res.json();
        if(data.api_key){apiKeyDisplay.className="success";apiKeyDisplay.textContent=`✅ Your API Key: ${data.api_key} (Limit: ${data.free_limit})`;copyKeyBtn.style.display="inline-block";copyKeyBtn.textContent="Copy Key";}
        else if(data.error){apiKeyDisplay.className="error";apiKeyDisplay.textContent=`❌ Error: ${data.error}`;copyKeyBtn.style.display="none";}
    }catch(err){apiKeyDisplay.className="error";apiKeyDisplay.textContent="❌ Error generating API key.";copyKeyBtn.style.display="none";}
};
copyKeyBtn.onclick=()=>{
    const keyText=apiKeyDisplay.textContent.split(":")[1]?.split("(")[0].trim();
    if(keyText){navigator.clipboard.writeText(keyText);copyKeyBtn.textContent="Copied!";setTimeout(()=>{copyKeyBtn.textContent="Copy Key";},2000);}
};
