<div align="center">

# PushBox 🚀

**PushBox: Your personal, secure cloud backup powered by GitHub.**

PushBox is a desktop application that lets you use your GitHub account as a free, fast, and reliable cloud backup solution. Create virtual folders, add your important files, and push them to private GitHub repositories with a single click.

</div>

---

## Features

-   **GitHub Integration**: Leverages your GitHub account to create and manage private repositories for backups.
-   **Virtual Folders**: Organize local files from different locations into logical "virtual folders" within the app without moving the original files.
-   **Direct Uploads**: Pushes your virtual folders to GitHub, creating a new private repository for each one.
-   **Asynchronous Thumbnails**: Fetches image thumbnails directly from GitHub in the background, ensuring the UI remains responsive and functional even after local files are deleted.
-   **Persistent Caching**: Caches thumbnails locally to speed up loading times and reduce API calls on subsequent launches.
-   **Secure Credential Storage**: Saves your GitHub username and Personal Access Token (PAT) locally for easy access.
-   **Simple Onboarding**: A quick and easy setup process to get you started.

---

## Screenshots
<img width="1327" height="908" alt="image" src="https://github.com/user-attachments/assets/2e00ca74-c1e7-44ff-9f93-d1adf27628f1" />
<img width="1308" height="888" alt="image" src="https://github.com/user-attachments/assets/bbd153cf-2837-4ba0-9364-ac6fef95e2cc" />


---

## How It Works

PushBox simplifies the backup process by automating Git and GitHub API interactions.

1.  **Authenticate**: You start by providing your GitHub username and a Personal Access Token (PAT) with `repo` permissions. These are stored locally for future use.
2.  **Organize**: Create a "virtual folder" inside the app. This is just a list that points to your local files; it doesn't move or duplicate them on your machine.
3.  **Add Files**: Add any files from your computer to your virtual folders.
4.  **Push to GitHub**: When you're ready, click "Push to GitHub." PushBox uses the GitHub API to:
    -   Create a new **private** repository on your GitHub account named after your virtual folder.
    -   Upload each file from your virtual folder into that repository.
5.  **View Backups**: Your files are now safely stored on GitHub. The app loads thumbnails directly from the repository, so you always have a visual confirmation of your backup.

---

## Getting Started

Follow these instructions to get a local copy up and running.

### Prerequisites

-   Python 3.8+
-   A GitHub Account
-   A GitHub Personal Access Token (PAT) with `repo` scope. You can create one [here](https://github.com/settings/tokens/new).

### Installation

1.  **Clone the repository:**
    ```sh
    git clone [https://github.com/your-username/pushbox.git](https://github.com/your-username/pushbox.git)
    cd pushbox
    ```

2.  **Create a virtual environment (recommended):**
    ```sh
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```

3.  **Install the required packages:**
    ```sh
    pip install -r requirements.txt
    ```
---

## Usage

1.  **Run the application:**
    ```sh
    python main.py
    ```

2.  **Onboarding**: The first time you launch, you'll see a brief onboarding guide.

3.  **Authentication**: Enter your GitHub username and Personal Access Token.

4.  **Create and Manage Backups**: Use the dashboard to create virtual folders, add files, and push them to GitHub.

---

## Configuration

The application stores its configuration and thumbnail cache in your user home directory:

-   **Config File (`.pushbox_config.json`)**: Stores your GitHub credentials and virtual folder structure.
-   **Cache Directory (`.pushbox_cache/`)**: Stores downloaded thumbnails to improve performance.

---

## Contributing

Contributions are welcome! Please feel free to fork the repository, make changes, and submit a pull request.

1.  Fork the Project
2.  Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3.  Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4.  Push to the Branch (`git push origin feature/AmazingFeature`)
5.  Open a Pull Request

---

## License

Distributed under the MIT License. See `LICENSE` for more information.
