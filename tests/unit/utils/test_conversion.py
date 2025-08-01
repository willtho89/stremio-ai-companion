"""
Tests for the conversion utility functions.
"""

from app.utils.conversion import movie_to_stremio_meta, tv_to_stremio_meta


class TestMovieToStremioMeta:
    """Tests for the movie_to_stremio_meta function."""

    def test_with_complete_data(self, sample_tmdb_movie):
        """Test conversion with complete movie data."""
        result = movie_to_stremio_meta(sample_tmdb_movie)

        assert result["id"] == "tmdb:550"
        assert result["type"] == "movie"
        assert result["name"] == "Fight Club"
        assert result["poster"] == "https://image.tmdb.org/t/p/w500/pB8BM7pdSp6B6Ih7QZ4DrQ3PmJK.jpg"
        assert result["background"] == "https://image.tmdb.org/t/p/w1280/hZkgoQYus5vegHoetLkCJzb17zJ.jpg"
        assert (
            result["description"]
            == "A ticking-time-bomb insomniac and a slippery soap salesman channel primal male aggression into a shocking new form of therapy."
        )
        assert result["releaseInfo"] == "1999"
        assert result["imdbRating"] == 8.4
        assert result["genre"] == ["Drama", "Thriller"]
        assert result["runtime"] == "139 min"

    def test_with_custom_poster(self, sample_tmdb_movie):
        """Test conversion with a custom poster URL."""
        custom_poster = "https://example.com/custom_poster.jpg"
        result = movie_to_stremio_meta(sample_tmdb_movie, custom_poster)

        assert result["poster"] == custom_poster

    def test_with_missing_poster_path(self, sample_tmdb_movie):
        """Test conversion with missing poster_path."""
        movie_data = sample_tmdb_movie.copy()
        movie_data.pop("poster_path")

        result = movie_to_stremio_meta(movie_data)

        assert "poster" not in result

    def test_with_missing_backdrop_path(self, sample_tmdb_movie):
        """Test conversion with missing backdrop_path."""
        movie_data = sample_tmdb_movie.copy()
        movie_data.pop("backdrop_path")

        result = movie_to_stremio_meta(movie_data)

        assert "background" not in result

    def test_with_missing_release_date(self, sample_tmdb_movie):
        """Test conversion with missing release_date."""
        movie_data = sample_tmdb_movie.copy()
        movie_data.pop("release_date")

        result = movie_to_stremio_meta(movie_data)

        assert "releaseInfo" not in result

    def test_with_missing_genres(self, sample_tmdb_movie):
        """Test conversion with missing genres."""
        movie_data = sample_tmdb_movie.copy()
        movie_data.pop("genres")

        result = movie_to_stremio_meta(movie_data)

        assert "genre" not in result

    def test_with_missing_runtime(self, sample_tmdb_movie):
        """Test conversion with missing runtime."""
        movie_data = sample_tmdb_movie.copy()
        movie_data.pop("runtime")

        result = movie_to_stremio_meta(movie_data)

        assert "runtime" not in result

    def test_with_minimal_data(self):
        """Test conversion with minimal movie data."""
        minimal_movie = {"id": 123, "title": "Minimal Movie"}

        result = movie_to_stremio_meta(minimal_movie)

        assert result["id"] == "tmdb:123"
        assert result["type"] == "movie"
        assert result["name"] == "Minimal Movie"
        assert "poster" not in result
        assert "background" not in result
        assert "releaseInfo" not in result
        assert "imdbRating" not in result
        assert "genre" not in result
        assert "runtime" not in result


class TestTVToStremioMeta:
    """Tests for the tv_to_stremio_meta function."""

    def test_with_complete_data(self, sample_tmdb_tv):
        """Test conversion with complete TV series data."""
        result = tv_to_stremio_meta(sample_tmdb_tv)

        assert result["id"] == "tmdb:1399"
        assert result["type"] == "series"
        assert result["name"] == "Game of Thrones"
        assert result["poster"] == "https://image.tmdb.org/t/p/w500/u3bZgnGQ9T01sWNhyveQz0wH0Hl.jpg"
        assert result["background"] == "https://image.tmdb.org/t/p/w1280/suopoADq0k8YZr4dQXcU6pToj6s.jpg"
        assert result["description"] == "Seven noble families fight for control of the mythical land of Westeros."
        assert result["releaseInfo"] == "2011"
        assert result["imdbRating"] == 9.3
        assert result["genre"] == ["Sci-Fi & Fantasy", "Drama", "Action & Adventure"]
        assert result["runtime"] == "60 min/ep"

    def test_with_custom_poster(self, sample_tmdb_tv):
        """Test conversion with a custom poster URL."""
        custom_poster = "https://example.com/custom_poster.jpg"
        result = tv_to_stremio_meta(sample_tmdb_tv, custom_poster)

        assert result["poster"] == custom_poster

    def test_with_multiple_episode_runtimes(self, sample_tmdb_tv):
        """Test conversion with multiple episode runtimes."""
        tv_data = sample_tmdb_tv.copy()
        tv_data["episode_run_time"] = [45, 60, 75]

        result = tv_to_stremio_meta(tv_data)

        assert result["runtime"] == "60 min/ep"  # Average of 45, 60, 75

    def test_with_missing_episode_runtime(self, sample_tmdb_tv):
        """Test conversion with missing episode runtime."""
        tv_data = sample_tmdb_tv.copy()
        tv_data.pop("episode_run_time")

        result = tv_to_stremio_meta(tv_data)

        assert "runtime" not in result

    def test_with_minimal_data(self):
        """Test conversion with minimal TV series data."""
        minimal_tv = {"id": 123, "name": "Minimal Series"}

        result = tv_to_stremio_meta(minimal_tv)

        assert result["id"] == "tmdb:123"
        assert result["type"] == "series"
        assert result["name"] == "Minimal Series"
        assert "poster" not in result
        assert "background" not in result
        assert "releaseInfo" not in result
        assert "imdbRating" not in result
        assert "genre" not in result
        assert "runtime" not in result
