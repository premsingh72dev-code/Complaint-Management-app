(function() {
    "use strict";

    /**
     * Easy selector helper function
     */
    const select = (el, all = false) => {
        el = el.trim()
        if (all) {
            return [...document.querySelectorAll(el)]
        } else {
            return document.querySelector(el)
        }
    }

    /**
     * Easy event listener function
     */
    const on = (type, el, listener, all = false) => {
        if (all) {
            select(el, all).forEach(e => e.addEventListener(type, listener))
        } else {
            select(el, all).addEventListener(type, listener)
        }
    }

    /**
     * Easy on scroll event listener 
     */
    const onscroll = (el, listener) => {
        el.addEventListener('scroll', listener)
    }

    /**
     * Sidebar toggle
     */
     if (select('.toggle-sidebar-btn')) {
        on('click', '.toggle-sidebar-btn', function(e) {
            select('body').classList.toggle('toggle-sidebar')
        })
    }


    /**
     * Search bar toggle
     */
    if (select('.search-bar-toggle')) {
        on('click', '.search-bar-toggle', function(e) {
            select('.search-bar').classList.toggle('search-bar-show')
        })
    }

    /**
     * Navbar links active state on scroll
     */
    let navbarlinks = select('#navbar .scrollto', true)
    const navbarlinksActive = () => {
        let position = window.scrollY + 200
        navbarlinks.forEach(navbarlink => {
            if (!navbarlink.hash) return
            let section = select(navbarlink.hash)
            if (!section) return
            if (position >= section.offsetTop && position <= (section.offsetTop + section.offsetHeight)) {
                navbarlink.classList.add('active')
            } else {
                navbarlink.classList.remove('active')
            }
        })
    }
    window.addEventListener('load', navbarlinksActive)
    onscroll(document, navbarlinksActive)

    /**
     * Toggle .header-scrolled class to #header when page is scrolled
     */
    let selectHeader = select('#header')
    if (selectHeader) {
        const headerScrolled = () => {
            if (window.scrollY > 100) {
                selectHeader.classList.add('header-scrolled')
            } else {
                selectHeader.classList.remove('header-scrolled')
            }
        }
        window.addEventListener('load', headerScrolled)
        onscroll(document, headerScrolled)
    }


    /**
     * Initiate Bootstrap validation check
     */
    var needsValidation = document.querySelectorAll('.needs-validation')

    Array.prototype.slice.call(needsValidation)
        .forEach(function(form) {
            form.addEventListener('submit', function(event) {
                if (!form.checkValidity()) {
                    event.preventDefault()
                    event.stopPropagation()
                }

                form.classList.add('was-validated')
            }, false)
        })

    /**
     * Initiate Datatables
     */
    // const datatables = select('.datatable', true);
    // datatables.forEach(datatable => {
    //     new simpleDatatables.DataTable(datatable, {
    //         paging: false
    //     });
    // })

    // const datatables1 = select('.datatable-order', true);
    // datatables1.forEach(datatable => {
    //     new simpleDatatables.DataTable(datatable, {
    //         paging: false,
    //         searchable: false
    //     });
    // })

})();

var mode = $('#dark_mode').is(':checked');

if(!mode){
    $('#dark_mode').prop("checked", false);
    $("table").removeClass("table-dark");
    $('.light-mode-login').removeClass('d-none');
    $('.dark-mode-login').addClass('d-none');
    $('#sidebar .sidebar-nav a').removeClass('dark-navBtn');
    $('#header, #sidebar').removeClass('header-dark');
    $('#header, #sidebar').addClass('header-light');
    $('.card-body').removeClass('dark-mode-card');
    $('.modal-content').removeClass('dark-mode-modal');
    $('#btn-close').removeClass('d-none');
}

if(localStorage.getItem("mode") == 'dark'){
    $('#dark_mode').prop("checked", true);
    $(document.body).toggleClass("dark-mode");
    $("table").addClass("table-dark");
    $('.card-body').addClass('dark-mode-card');
    $('.light-mode-login').addClass('d-none');
    $('.dark-mode-login').removeClass('d-none');
    $('#sidebar .sidebar-nav a').addClass('dark-navBtn');
    $('#header, #sidebar').removeClass('header-light');
    $('#header, #sidebar').addClass('header-dark');
    $('.modal-content').addClass('dark-mode-modal');
    $('#btn-close').addClass('d-none');
}else if(localStorage.getItem("mode") == 'light'){
    $('#dark_mode').prop("checked", false);
    $("table").removeClass("table-dark");
    $('.light-mode-login').removeClass('d-none');
    $('.dark-mode-login').addClass('d-none');
    $('#sidebar .sidebar-nav a').removeClass('dark-navBtn');
    $('#header, #sidebar').removeClass('header-dark');
    $('#header, #sidebar').addClass('header-light');
    $('.card-body').removeClass('dark-mode-card');
    $('.modal-content').removeClass('dark-mode-modal');
    $('#btn-close').removeClass('d-none');
}

$(document).on('change', '#dark_mode', function(){
    mode = $(this).is(':checked');
    $(document.body).toggleClass("dark-mode");
    if(mode){
        localStorage.setItem('mode','dark');
        $("table").addClass("table-dark");
        $('.light-mode-login').addClass('d-none');
        $('.dark-mode-login').removeClass('d-none');
        $('#sidebar .sidebar-nav a').addClass('dark-navBtn');
        $('#header, #sidebar').addClass('header-dark');
        $('#header, #sidebar').removeClass('header-light');
        $('.card-body').addClass('dark-mode-card');
        $('.modal-content').addClass('dark-mode-modal');
        $('#btn-close').addClass('d-none');
    }else{
        localStorage.setItem('mode','light');
        $("table").removeClass("table-dark");
        $('.light-mode-login').removeClass('d-none');
        $('.dark-mode-login').addClass('d-none');
        $('#sidebar .sidebar-nav a').removeClass('dark-navBtn');
        $('#header, #sidebar').removeClass('header-dark');
        $('#header, #sidebar').addClass('header-light');
        $('.card-body').removeClass('dark-mode-card');
        $('.modal-content').removeClass('dark-mode-modal');
        $('#btn-close').addClass('d-none');
    }
})

