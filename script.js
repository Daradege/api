document.addEventListener("DOMContentLoaded", function() {
    const popup_json = "/popup.json"
    fetch(popup_json)
        .then(response => response.json())
        .then(data => {
            if (data.show) {
                showNotification({
                    type: data.type,
                    title: data.title,
                    message: data.message,
                    duration: data.duration,
                    closable: data.closable,
                })
            }
        })
})

function toggleApiSelect() {
    const reportType = document.getElementById('reportType').value;
    const apiSelectContainer = document.getElementById('apiSelectContainer');
    apiSelectContainer.style.display = reportType === 'bug' ? 'block' : 'none';
}

function submitReport(event) {
    event.preventDefault();

    const reportType = document.getElementById('reportType').value;
    const apiSelect = document.getElementById('apiSelect').value;
    const description = document.getElementById('description').value;
    const contact = document.getElementById('contact').value;

    const data = {
        type: reportType,
        api: reportType === 'bug' ? apiSelect : null,
        description: description,
        contact: contact
    };

    fetch('/bug-report', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data),
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.text().then(text => {
                return text ? JSON.parse(text) : {};
            });
        })
        .then(data => {
            alert('Report submitted successfully!');
            document.getElementById('reportForm').reset();
        })
        .catch((error) => {
            alert('Error submitting report: ' + error);
        });
}

const baseUrl = "https://api.devnw.ir/";

var api_file_json = "/apilist.json";

function fetchApiEndpoints() {
    fetch(api_file_json)
        .then(response => response.json())
        .then(data => {
            apiEndpoints = data || [];
            if (apiEndpoints && apiEndpoints.length > 0) {
                apiEndpoints.forEach(item => {
                    if (item.example) {
                        item.example = item.example.replace('${baseUrl}', baseUrl);
                    }
                });
                generateEndpoints();
            } else {
                console.error("No endpoints found in API response");
            }
        })
        .catch(error => {
            console.error("Error fetching API endpoints:", error);
        });
}

let apiEndpoints = [];

fetchApiEndpoints();


function generateEndpoints() {
    const container = document.getElementById("endpoints-container");

    apiEndpoints.forEach(endpoint => {
        const endpointDiv = document.createElement("div");
        endpointDiv.classList.add("endpoint");
        endpointDiv.id = endpoint.title.toLowerCase().replace(/\s+/g, '-');
        endpointDiv.classList.add("endpoint");

        const headerDiv = document.createElement("div");
        headerDiv.classList.add("endpoint-header");

        const titleElement = document.createElement("h2");
        titleElement.textContent = endpoint.title;

        const chevronSvg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
        chevronSvg.setAttribute("class", "chevron");
        chevronSvg.setAttribute("width", "24");
        chevronSvg.setAttribute("height", "24");
        chevronSvg.setAttribute("viewBox", "0 0 24 24");
        chevronSvg.setAttribute("fill", "none");
        chevronSvg.setAttribute("stroke", "currentColor");
        chevronSvg.setAttribute("stroke-width", "2");
        chevronSvg.setAttribute("stroke-linecap", "round");
        chevronSvg.setAttribute("stroke-linejoin", "round");

        const polyline = document.createElementNS("http://www.w3.org/2000/svg", "polyline");
        polyline.setAttribute("points", "6 9 12 15 18 9");
        chevronSvg.appendChild(polyline);

        headerDiv.appendChild(titleElement);
        headerDiv.appendChild(chevronSvg);

        const contentDiv = document.createElement("div");
        contentDiv.classList.add("endpoint-content");

        const methodElement = document.createElement("p");
        methodElement.innerHTML = `<span class="method">${endpoint.method}</span> ${endpoint.url}`;

        const descriptionElement = document.createElement("p");
        descriptionElement.textContent = endpoint.description;

        let parametersHtml = "";
        if (endpoint.parameters.length > 0) {
            parametersHtml += "<p>Parameters:</p><ul>";
            endpoint.parameters.forEach(param => {
                parametersHtml += `<li><code>${param.name}</code> (${param.required ? "required" : "optional"}): ${param.description}</li>`;
            });
            parametersHtml += "</ul>";
        }

        const returnsElement = document.createElement("p");
        returnsElement.textContent = `Returns: ${endpoint.returns}`;

        const exampleDiv = document.createElement("div");
        exampleDiv.classList.add("example");
        exampleDiv.innerHTML = `Example request:<br><code>GET ${endpoint.example}</code>`;

        const copyButton = document.createElement("button");
        copyButton.innerHTML = `
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                        <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                    </svg>
                    <span>Copy URL</span>
                `;
        copyButton.classList.add("copy-button");
        copyButton.style.display = "flex";
        copyButton.style.alignItems = "center";
        copyButton.style.gap = "8px";
        copyButton.style.padding = "8px 16px";
        copyButton.style.border = "1px solid #ddd";
        copyButton.style.borderRadius = "4px";
        copyButton.style.backgroundColor = "#f8f9fa";
        copyButton.style.cursor = "pointer";
        copyButton.style.transition = "all 0.2s ease";

        copyButton.onmouseover = () => {
            copyButton.style.backgroundColor = "#e9ecef";
            copyButton.style.borderColor = "#ced4da";
        };

        copyButton.onmouseout = () => {
            copyButton.style.backgroundColor = "#f8f9fa";
            copyButton.style.borderColor = "#ddd";
        };

        copyButton.onclick = () => {
            navigator.clipboard.writeText(endpoint.example);
            const originalContent = copyButton.innerHTML;
            copyButton.innerHTML = `
                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <polyline points="20 6 9 17 4 12"></polyline>
                        </svg>
                        <span>Copied!</span>
                    `;
            copyButton.style.backgroundColor = "#d4edda";
            copyButton.style.borderColor = "#c3e6cb";
            copyButton.style.color = "#155724";

            setTimeout(() => {
                copyButton.innerHTML = originalContent;
                copyButton.style.backgroundColor = "#f8f9fa";
                copyButton.style.borderColor = "#ddd";
                copyButton.style.color = "inherit";
            }, 2000);
        };

        contentDiv.innerHTML = `
                    ${methodElement.outerHTML}
                    ${descriptionElement.outerHTML}
                    ${parametersHtml}
                    ${returnsElement.outerHTML}
                `;
        contentDiv.appendChild(exampleDiv);
        contentDiv.appendChild(copyButton);

        endpointDiv.appendChild(headerDiv);
        endpointDiv.appendChild(contentDiv);

        container.appendChild(endpointDiv);
    });


    document.querySelectorAll(".endpoint-header").forEach(header => {
        header.addEventListener("click", () => {
            const endpoint = header.parentElement;
            endpoint.classList.toggle("active");
            const id = endpoint.id;
            window.location.hash = id;
        });
    });


    if (window.location.hash) {
        const id = window.location.hash.substring(1);
        const endpoint = document.getElementById(id);
        if (endpoint) {
            endpoint.classList.add("active");
            endpoint.scrollIntoView();
        }
    }
}


generateEndpoints();