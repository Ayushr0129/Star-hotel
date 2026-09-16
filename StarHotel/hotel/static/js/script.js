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
                this.items.forEach(i => i.classList.remove('active'));
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
const tabPanels = document.querySelectorAll('.tab-panel');

function moveTabHighlight(activeTab) {
    tabHighlight.style.left = activeTab.offsetLeft + 'px';
    tabHighlight.style.width = activeTab.offsetWidth + 'px';
}

function showPanel(tabKey) {
    tabPanels.forEach(panel => {
        panel.hidden = panel.dataset.tab !== tabKey;
    });
}

function updateHero(tabButton) {
    const heroImg = document.getElementById('heroImg');
    const heroSrc = tabButton.dataset.hero;
    if (heroImg && heroSrc) {
        heroImg.src = heroSrc;
    }
}

const initialTab = document.querySelector('.tab-item.active');
if (initialTab) {
    moveTabHighlight(initialTab);
    showPanel(initialTab.dataset.tab);
    updateHero(initialTab);
}

if (document.querySelector('.tab-item.active')) {
    moveTabHighlight(document.querySelector('.tab-item.active'));
}

tabs.forEach(tab => {
    tab.addEventListener('click', function () {
        tabs.forEach(t => t.classList.remove('active'));
        this.classList.add('active');
        moveTabHighlight(this);
        showPanel(this.dataset.tab);
        updateHero(this);
    });
});


document.querySelectorAll('.btn-book').forEach(btn => {
    btn.addEventListener('click', () => {
        const card = btn.closest('.room-card');
        const name = card.dataset.name;
        const price = Number(card.dataset.price);

        document.getElementById('cartItems').innerHTML = `
            <div class="cart-item">
                <p class="cart-item-name">${name}</p>
                <p class="cart-item-nights">1 night</p>
            </div>
        `;
        document.getElementById('cartTotal').textContent = `Rs ${price.toLocaleString('en-IN')}`;
    });
});