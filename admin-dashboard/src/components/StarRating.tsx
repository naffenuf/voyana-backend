interface StarRatingProps {
  rating: number;
  maxRating?: number;
  size?: 'small' | 'medium' | 'large';
  showValue?: boolean;
}

export default function StarRating({
  rating,
  maxRating = 5,
  size = 'small',
  showValue = false,
}: StarRatingProps) {
  const sizeClasses = {
    small: 'text-sm',
    medium: 'text-base',
    large: 'text-xl',
  };

  const renderStars = () => {
    const stars = [];
    const fullStars = Math.floor(rating);
    const hasHalfStar = rating % 1 >= 0.5;

    // Full stars
    for (let i = 0; i < fullStars; i++) {
      stars.push(
        <span key={`full-${i}`} className="text-yellow-500">
          ★
        </span>
      );
    }

    // Half star
    if (hasHalfStar && fullStars < maxRating) {
      stars.push(
        <span key="half" className="text-yellow-500">
          ★
        </span>
      );
    }

    // Empty stars
    const emptyStars = maxRating - fullStars - (hasHalfStar ? 1 : 0);
    for (let i = 0; i < emptyStars; i++) {
      stars.push(
        <span key={`empty-${i}`} className="text-gray-300">
          ★
        </span>
      );
    }

    return stars;
  };

  return (
    <div className={`inline-flex items-center gap-1 ${sizeClasses[size]}`}>
      <span className="inline-flex">{renderStars()}</span>
      {showValue && (
        <span className="text-gray-600 font-medium ml-1">
          {rating.toFixed(1)}
        </span>
      )}
    </div>
  );
}
