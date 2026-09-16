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
                this.item.forEach(i => i.classList.remove('active'));
                item.classList.add('active');
                this.moveHighlight(item);
            
            });
        });
    }
}

/*this is for general header */

new SidebarNav('nav', 'navHighlight');


class SiteNavPill {
  constructor(navId, pillId, defaultId) {
    this.nav = document.getElementById(navId);
    this.pill = document.getElementById(pillId);
 
    if (!this.nav || !this.pill) return;
 
    this.items = this.nav.querySelectorAll('.site-nav-item');
    this.defaultItem = document.getElementById(defaultId) || this.items[this.items.length - 1];
    this.init();
  }
 
  movePill(item) {
    this.items.forEach(i => i.classList.remove('on-pill'));
    item.classList.add('on-pill');
    this.pill.style.left = item.offsetLeft + 'px';
    this.pill.style.width = item.offsetWidth + 'px';
  }
 
  init() {
    window.addEventListener('DOMContentLoaded', () => this.movePill(this.defaultItem));
 
    this.items.forEach(item => {
      item.addEventListener('mouseenter', () => this.movePill(item));
    });
 
    this.nav.addEventListener('mouseleave', () => this.movePill(this.defaultItem));
  }
}
 
new SiteNavPill('siteNav', 'navPill', 'registerLink');
   
/*Home booking animation*/

const tabs = document.querySelectorAll('.tab-item');
const tabHighlight = document.getElementById('tabHighlight');

function moveTabHighlight(activeTab) {
    tabHighlight.style.left = activeTab.offsetLeft + 'px';
    tabHighlight.style.width = activeTab.offsetWidth + 'px';
}

// position on load
if (document.querySelector('.tab-item.active')) {
    moveTabHighlight(document.querySelector('.tab-item.active'));
}

tabs.forEach(tab => {
    tab.addEventListener('click', function () {
        tabs.forEach(t => t.classList.remove('active'));
        this.classList.add('active');
        moveTabHighlight(this);
    });
});