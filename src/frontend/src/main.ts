import { handleNavigation } from './router';

const initApp = (): void => {
    document.body.addEventListener('click', (e: MouseEvent) => {
        //クリックされた要素に最も近いaタグのdata-link属性を持つものを取得
        //closestは、引数に指定したセレクタに一致する要素で最も近いものを返すメソッド
        const target = (e.target as HTMLElement).closest('a[data-link]');
        if (target instanceof HTMLAnchorElement) {
            e.preventDefault();
            const url = target.getAttribute('href');
            if (url) {
                // urlに書き換える
                window.history.pushState({}, '', url);
                handleNavigation();
            }
        }
    });
    window.addEventListener('popstate', handleNavigation);

    handleNavigation();
};

document.addEventListener('DOMContentLoaded', initApp);