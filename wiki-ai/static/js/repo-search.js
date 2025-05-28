document.addEventListener('DOMContentLoaded', function() {
    const searchRepository = document.getElementById('searchRepository');
    const searchResults = document.getElementById('searchResults');
    const repositoryUrl = document.getElementById('repositoryUrl');
    const submitRepoUrl = document.getElementById('submitRepoUrl');
    const addRepositoryModal = document.getElementById('addRepositoryModal');
    const modal = bootstrap.Modal.getOrCreateInstance(addRepositoryModal);

    let searchTimeout;

    // Repository search functionality
    searchRepository.addEventListener('input', function() {
        clearTimeout(searchTimeout);
        const query = this.value.trim();
        
        if (query.length < 2) {
            searchResults.classList.add('d-none');
            // Enable the repository URL input and button when search is not active
            repositoryUrl.disabled = false;
            submitRepoUrl.disabled = false;
            return;
        }

        // Disable the repository URL input and button when search is active
        repositoryUrl.disabled = true;
        submitRepoUrl.disabled = true;

        searchTimeout = setTimeout(async () => {
            try {
                const response = await fetch(`/search?q=${encodeURIComponent(query)}`);
                const results = await response.json();
                
                if (results.length > 0) {
                    displaySearchResults(results);
                } else {
                    searchResults.innerHTML = '<div class="list-group-item">No repositories found</div>';
                    searchResults.classList.remove('d-none');
                }
            } catch (error) {
                console.error('Error searching repositories:', error);
            } finally {
                // Re-enable the repository URL input and button when search is complete
                repositoryUrl.disabled = false;
                submitRepoUrl.disabled = false;
            }
        }, 300);
    });

    // URL submission handler
    submitRepoUrl.addEventListener('click', function() {
        const url = repositoryUrl.value.trim();
        const match = url.match(/github\.com\/([^/]+)\/([^/]+)/);
        
        if (match) {
            const [, owner, name] = match;
            addRepository(owner, name.replace(/\.git$/, ''));
        } else {
            alert('Please enter a valid GitHub repository URL');
        }
    });

    // Click outside search results handler
    document.addEventListener('click', function(e) {
        if (!searchResults.contains(e.target) && e.target !== searchRepository) {
            searchResults.classList.add('d-none');
        }
    });

    // Handle repository removal
    document.addEventListener('click', async function(e) {
        const removeButton = e.target.closest('.remove-repo');
        if (!removeButton) return;
        
        e.preventDefault();
        const owner = removeButton.dataset.owner;
        const name = removeButton.dataset.name;
        const isDefault = removeButton.dataset.default === 'true';
        
        // Prevent removal of default repositories
        if (isDefault) {
            return;
        }
        
        // Store the repo info and button reference
        repoToRemove = { owner, name, button: removeButton };
        
        // Update confirmation modal content
        document.getElementById('repoFullName').textContent = `${owner}/${name}`;
        
        // Show confirmation modal
        confirmationModal.show();
    });

    function displaySearchResults(repos) {
        searchResults.innerHTML = '';
        searchResults.classList.add('list-group', 'shadow-sm');
        
        repos.forEach(repo => {
            const item = document.createElement('div');
            item.className = 'list-group-item list-group-item-action';
            if (repo.is_added) {
                item.classList.add('bg-light');
            }
            console.log("repo data:", repo);
            item.innerHTML = `
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <strong>${repo.full_name}</strong>
                        <br>
                        <small class="text-muted">${repo.description || 'No description'}</small>
                    </div>
                    ${repo.is_added ? 
                        '<span class="badge bg-success">Added</span>' :
                        '<button class="btn btn-sm btn-primary add-repo-btn">Add</button>'
                    }
                </div>
            `;
            
            if (!repo.is_added) {
                const addButton = item.querySelector('.add-repo-btn');
                addButton.addEventListener('click', () => {
                    addRepository(repo.owner, repo.name);
                });
            }
            
            searchResults.appendChild(item);
        });
        
        searchResults.classList.remove('d-none');
    }

    async function addRepository(owner, name) {
        try {
            const response = await fetch('/repo/add', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    owner: owner,
                    name: name
                })
            });
            
            if (response.ok) {
                modal.hide();
                // Refresh the page to show the newly added repository
                window.location.reload();
            } else {
                const data = await response.json();
                alert(data.detail || 'Failed to add repository');
            }
        } catch (error) {
            console.error('Error adding repository:', error);
            alert('Failed to add repository');
        }
    }
});
