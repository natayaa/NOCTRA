AOS.init({
  duration: 1000,
  once: true
});

const navbar = document.querySelector("nav");

window.addEventListener("scroll", () => {

  if(window.scrollY > 30){

    navbar.style.background = "rgba(4,8,22,.92)";

  } else {

    navbar.style.background = "rgba(4,8,22,.6)";
  }

});