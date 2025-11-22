document.addEventListener('DOMContentLoaded', function () {
    const form = document.getElementById('videoForm');
    const submitBtn = document.getElementById('submitBtn');
    const btnText = submitBtn.querySelector('.btn-text');
    const btnLoader = submitBtn.querySelector('.btn-loader');
    const statusMessage = document.getElementById('statusMessage');
    const resultSection = document.getElementById('resultSection');

    form.addEventListener('submit', async function (e) {
        e.preventDefault();

        // Get form data
        const formData = {
            script: document.getElementById('script').value,
            voice_provider: document.getElementById('voiceProvider').value,
            voice_id: document.getElementById('voiceId').value,
            gameplay_video_path: document.getElementById('videoPath').value,
            reference_audio_path: document.getElementById('referenceAudio').value || null
        };

        // Show loading state
        submitBtn.disabled = true;
        btnText.style.display = 'none';
        btnLoader.style.display = 'inline-block';

        // Hide previous results
        resultSection.style.display = 'none';

        // Show processing message
        showStatus('Processing your video... This may take a few minutes.', 'info');

        try {
            const response = await fetch('/process_script', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(formData)
            });

            const result = await response.json();

            if (response.ok) {
                // Success!
                showStatus('Video generated successfully! 🎉', 'success');

                // Show result section
                document.getElementById('jobId').textContent = result.job_id;
                document.getElementById('downloadLink').href = result.output_url;
                resultSection.style.display = 'block';

                // Scroll to results
                resultSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            } else {
                // Error from server
                showStatus(`Error: ${result.detail || 'Something went wrong'}`, 'error');
            }
        } catch (error) {
            // Network or other error
            showStatus(`Error: ${error.message}. Please check if the server is running.`, 'error');
        } finally {
            // Reset button state
            submitBtn.disabled = false;
            btnText.style.display = 'inline-block';
            btnLoader.style.display = 'none';
        }
    });

    function showStatus(message, type) {
        statusMessage.textContent = message;
        statusMessage.className = `status-message ${type}`;
        statusMessage.style.display = 'block';
    }

    // Update voice ID placeholder based on provider selection
    const voiceProvider = document.getElementById('voiceProvider');
    const voiceId = document.getElementById('voiceId');
    const voiceHelp = voiceId.nextElementSibling;

    voiceProvider.addEventListener('change', function () {
        const provider = this.value;

        if (provider === 'openai') {
            voiceId.value = 'alloy';
            voiceId.placeholder = 'e.g., alloy, echo, fable';
            voiceHelp.textContent = 'OpenAI: alloy, echo, fable, onyx, nova, shimmer';
        } else if (provider === 'elevenlabs') {
            voiceId.value = 'JBFqnCBsd6RMkjVDRZzb';
            voiceId.placeholder = 'e.g., JBFqnCBsd6RMkjVDRZzb';
            voiceHelp.textContent = 'ElevenLabs: Use voice ID from your account';
        } else if (provider === 'runpod') {
            voiceId.value = '';
            voiceId.placeholder = 'Enter predefined voice ID';
            voiceHelp.textContent = 'RunPod: Enter your custom voice ID or leave empty';
        }
    });
});
