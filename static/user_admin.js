document.addEventListener("DOMContentLoaded", function () {
    function toggleGroupField() {
        const roleSelect = document.getElementById("id_role");
        const groupField = document.querySelector(".form-row.field-group");

        if (!roleSelect || !groupField) return;

        if (roleSelect.value === "student") {
            groupField.style.display = "";
        } else {
            groupField.style.display = "none";
            const groupInput = document.getElementById("id_group");
            if (groupInput) groupInput.value = "";
        }
    }

    const roleSelect = document.getElementById("id_role");
    if (roleSelect) {
        roleSelect.addEventListener("change", toggleGroupField);
        toggleGroupField();
    }
});
