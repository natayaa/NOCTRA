// ACTIVE SIDEBAR

const currentPath =
window.location.pathname;

document
.querySelectorAll(".sidebar-nav a")
.forEach(link => {

    const href =
    link.getAttribute("href");

    if(href === currentPath){

        link.classList.add("active");
    }

});


// GLOBAL SEARCH

const searchInput =
document.querySelector(
".search-box input"
);

if(searchInput){

    searchInput.addEventListener(
        "keyup",
        e => {

            console.log(
                "Searching:",
                e.target.value
            );

        }
    );

}


// MOBILE SIDEBAR

const sidebar =
document.querySelector(".sidebar");

const menuBtn =
document.querySelector(".menu-btn");

if(menuBtn){

    menuBtn.addEventListener(
        "click",
        () => {

            sidebar.classList.toggle(
                "open"
            );

        }
    );

}


// TOAST SYSTEM

function showToast(
    message,
    type = "success"
){

    const toast =
    document.createElement("div");

    toast.className =
    `toast ${type}`;

    toast.innerText =
    message;

    document.body
    .appendChild(toast);

    setTimeout(() => {

        toast.remove();

    },3000);
}


// EXAMPLE

window.showToast =
showToast;