import React from 'react';

const LoadingSpinner = ({ size = 'medium', color = 'primary' }) => {
  const getSizeClasses = () => {
    switch (size) {
      case 'small':
        return 'w-4 h-4 border-2';
      case 'large':
        return 'w-12 h-12 border-4';
      case 'xlarge':
        return 'w-16 h-16 border-4';
      default:
        return 'w-6 h-6 border-4';
    }
  };

  const getColorClasses = () => {
    switch (color) {
      case 'white':
        return 'text-white border-white border-t-transparent';
      case 'secondary':
        return 'text-secondary-600 border-secondary-600 border-t-transparent';
      default:
        return 'text-primary-600 border-primary-600 border-t-transparent';
    }
  };

  return (
    <div 
      className={`
        animate-spin inline-block rounded-full border-solid
        ${getSizeClasses()} 
        ${getColorClasses()}
      `}
      role="status"
      aria-label="Loading"
    >
      <span className="sr-only">Loading...</span>
    </div>
  );
};

export default LoadingSpinner;