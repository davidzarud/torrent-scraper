document.addEventListener('DOMContentLoaded', () => {
    const watchlistIcons = document.querySelectorAll('.watchlist-icon');

    watchlistIcons.forEach(icon => {
        icon.addEventListener('click', function() {
            const iconElement = this.querySelector('i');
            const movieId = this.getAttribute('data-movie-id'); // Get the movie ID

            // Add a transition effect when changing icons
            iconElement.classList.add('icon-transition');

            setTimeout(() => {
                if (iconElement.classList.contains('far')) {
                    // Add to watchlist
                    iconElement.classList.remove('far');
                    iconElement.classList.add('fas');
                    action = 'add';
                } else {
                    // Remove from watchlist
                    iconElement.classList.remove('fas');
                    iconElement.classList.add('far');
                    action = 'remove';
                }

                iconElement.classList.remove('icon-transition');
                iconElement.classList.add('icon-transition-active');

                toggleWatchlist(action, movieId)
            }, 150);

            setTimeout(() => {
                iconElement.classList.remove('icon-transition-active');
            }, 300);
        });
    });
});

function toggleWatchlist(action, movieId) {
    $.ajax({
            url: `/tmdb/watchlist/movie/${action}/${movieId}`,
            type: 'POST',
            contentType: 'application/json'
    });
}