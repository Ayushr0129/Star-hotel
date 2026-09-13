class SidebarNav {
    constructor(navId, highlightId) {
        this.nav = document.getElementById(navId);
        this.highlight = document.getElementById(highlightId);

        //If page does not have side bar do nothing

        if (!this.nav || !this.highlight) return;

        this.items = this.nav.querySelectorAll('.nav-item');
        this.init();

    }

    moveHighlight(item) {
        this.highlight.style.top = item.offsetTop + 'px';

    }

    init() {
        window.addEventListener('DOMContentLoaded', () => {
            const active = this.nav.querySelector('.nav-item.active')|| this.items[0];
            this.moveHighlight(active);
        });

        this.items.forEach(item => {
            item.addEventListener('click', (e) => {
                e.preventDefault();
                this.item.forEach(i => i.classList.remove('active'));
                item.classList.add('active');
                this.moveHighlight(item);
            
            });
        });
    }
}

new SidebarNav('nav', 'navHighlight');


                
