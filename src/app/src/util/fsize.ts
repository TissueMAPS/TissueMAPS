angular.module('tmaps.ui')
.filter('fsize', () => {
    return (input) => {
        var mb = input / 1000000;
        return Math.round(mb * 100) / 100 + ' MB';
    };
});
