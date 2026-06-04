class SettingsManager {

    constructor() {

        this.form =
            document.getElementById(
                "settingsForm"
            );

        this.saveButton =
            document.getElementById(
                "saveSettings"
            );

        this.resetButton =
            document.getElementById(
                "resetSettings"
            );

        this.status =
            document.getElementById(
                "saveStatus"
            );

        this.isDirty = false;

        this.registerEvents();

    }

    registerEvents() {

        this.form.addEventListener(
            "input",
            () => this.markDirty()
        );

        this.form.addEventListener(
            "change",
            () => this.markDirty()
        );

        this.saveButton.addEventListener(
            "click",
            () => this.save()
        );

        this.resetButton.addEventListener(
            "click",
            () => this.load()
        );

    }

    markDirty() {

        if (this.isDirty) {
            return;
        }

        this.isDirty = true;

        this.status.textContent =
            "Unsaved changes";

    }

    async load() {

        try {

            this.setStatus(
                "Loading settings..."
            );

            const response =
                await fetch(
                    "/api/settings"
                );

            if (!response.ok) {
                throw new Error();
            }

            const data =
                await response.json();

            this.populate(data);

            this.isDirty = false;

            this.setStatus(
                "Settings loaded",
                "success"
            );

        } catch {

            this.setStatus(
                "Unable to load settings",
                "error"
            );

        }

    }

    populate(data) {

        Object.entries(data)
            .forEach(
                ([key, value]) => {

                    const field =
                        this.form.elements[key];

                    if (!field) {
                        return;
                    }

                    if (
                        field.type ===
                        "checkbox"
                    ) {

                        field.checked =
                            Boolean(value);

                        return;

                    }

                    field.value = value;

                }
            );

    }

    async save() {

        try {

            this.saveButton.disabled =
                true;

            this.setStatus(
                "Saving..."
            );

            const payload =
                Object.fromEntries(
                    new FormData(
                        this.form
                    )
                );

            this.form
                .querySelectorAll(
                    'input[type="checkbox"]'
                )
                .forEach(
                    checkbox => {

                        payload[
                            checkbox.name
                        ] =
                            checkbox.checked;

                    }
                );

            const response =
                await fetch(
                    "/api/settings",
                    {
                        method: "PUT",
                        headers: {
                            "Content-Type":
                                "application/json"
                        },
                        body: JSON.stringify(
                            payload
                        )
                    }
                );

            if (!response.ok) {
                throw new Error();
            }

            this.isDirty = false;

            this.setStatus(
                "Settings saved successfully",
                "success"
            );

        } catch {

            this.setStatus(
                "Failed to save settings",
                "error"
            );

        } finally {

            this.saveButton.disabled =
                false;

        }

    }

    setStatus(
        message,
        type = ""
    ) {

        this.status.className =
            "save-status";

        if (type) {
            this.status.classList.add(
                type
            );
        }

        this.status.textContent =
            message;

    }

}

document.addEventListener(
    "DOMContentLoaded",
    () => {

        const settings =
            new SettingsManager();

        settings.load();

    }
);